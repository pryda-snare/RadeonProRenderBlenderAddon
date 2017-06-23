import datetime
import time
import traceback
import weakref
from pathlib import Path

import bpy
import numpy as np
import pyrpr
import viewportdraw

import rprblender.render
import rprblender.render.render_layers
import rprblender.render.render_stamp
import rprblender.render.scene
import rprblender.render.viewport
from rprblender import rpraddon, logging, config, sync, export
from rprblender.helpers import CallLogger
from rprblender.timing import TimedContext

call_logger = CallLogger(tag='render.engine')


@rpraddon.register_class
class RenderViewport(bpy.types.Operator):
    bl_idname = "rpr.view_render_start"
    bl_label = "RPR Start Viewport Render"

    def execute(self, context):
        start_viewport_rendering(context)
        return {'FINISHED'}


@call_logger.logged
def start_viewport_rendering(context):
    viewport_renderer = rprblender.render.viewport.ViewportRenderer()
    logging.debug('start: {},{}'.format(context.region.width, context.region.height), tag='render.viewport')
    viewport_renderer.set_render_aov(bpy.context.scene.rpr.render)
    viewport_renderer.set_render_resolution((context.region.width, context.region.height))
    viewport_renderer.set_render_camera(sync.extract_viewport_render_camera(context, context.scene.rpr.render))
    viewport_renderer.start(context.scene)

    RPREngine.viewport_renderers[context.space_data] = viewport_renderer


@rpraddon.register_class
class RPREngine(bpy.types.RenderEngine):
    bl_idname = 'RPR'
    bl_label = 'Radeon ProRender'
    bl_use_preview = True
    bl_preview = True

    # bl_use_shading_nodes = True
    bl_use_shading_nodes_custom = True

    # when something bad happens in api call(render, view_update etc) this one is set instead of
    # just pasing exception to Blender(where it's swallowed though displayed in stderr but
    # RenderEngine is shutdown not nicely after this)
    error = None

    viewport_renderers = {}
    viewportrenderer_space_data = None

    instances = weakref.WeakSet()  # for tests

    def __init__(self):
        super().__init__()
        logging.debug(self, "__init__")
        self.im = None
        self.texture = None

    @call_logger.logged
    def __del__(self):
        if self.viewportrenderer_space_data:
            viewport_renderer = self.viewport_renderers.pop(self.viewportrenderer_space_data)
            logging.debug('stopping:', viewport_renderer)
            viewport_renderer.stop()

    def update(self, data=None, scene=None):  # Export scene data for render
        if self.is_preview:
            logging.debug("create scene for preview render")
        else:
            logging.debug("create scene for normal render")

        logging.debug('update')

    def bake(self, scene, object, pass_type, pass_filter, object_id, pixel_array, num_pixels, depth,
             result):  # Bake passes
        logging.debug('bake')

    def render(self, scene):
        logging.debug('render')
        try:
            self._render(scene)
        except:
            self.report_render_error('render', "Exception: %s" % traceback.format_exc())

    @staticmethod
    def init_preview_settings():
        ibl = bpy.context.scene.rpr.render_preview.environment.ibl
        ibl.use_ibl_map = True
        ibl.ibl_map = str(Path(rprblender.__file__).parent / 'img/env.hdr')
        ibl.maps.background_map = str(Path(rprblender.__file__).parent / 'img/gray.jpg')

    def show_gpu_info(self):
        from . import helpers
        # import rprblender.helpers
        info = helpers.render_resources_helper.get_used_gpu_info()
        if info:
            self.report({'WARNING'}, info)
            logging.info('info: ', info)

    @call_logger.logged
    def _render(self, scene: bpy.types.Scene):
        logging.debug('render', 'preview' if self.is_preview else 'prod')

        if self.is_preview and not config.preview_enable:
            return

        if not self.is_preview:
            self.update_stats('starting render', 'Radeon ProRender')
            self.show_gpu_info()

        self.report({'INFO'}, "RPR: rendering " + ('PREVIEW' if self.is_preview else "PRODUCTION"))

        width = int(scene.render.resolution_x * scene.render.resolution_percentage / 100.0)
        height = int(scene.render.resolution_y * scene.render.resolution_percentage / 100.0)

        settings = bpy.context.scene.rpr.render_preview if self.is_preview else scene.rpr.render  # type: rprblender.properties.RenderSettings

        with rprblender.render.core_operations(raise_error=True):
            scene_renderer = rprblender.render.scene.SceneRenderer(settings, not self.is_preview)  #

        scene_synced = sync.SceneSynced(scene_renderer.core_context, scene, settings)

        scene_renderer.production_render = True

        render_resolution = (width, height)

        render_camera = sync.RenderCamera()
        sync.extract_render_camera_from_blender_camera(scene.camera, render_camera, render_resolution, 1, settings,
                                                       scene)

        scene_synced.set_render_camera(render_camera)

        aov_settings = rprblender.render.render_layers.extract_settings(
                scene_renderer.render_settings)
        with rprblender.render.core_operations(raise_error=True):
            scene_synced.make_core_scene()

            scene_renderer.update_aov(aov_settings)
            scene_renderer.update_render_resolution(render_resolution)

        try:
            if not self.is_preview:
                self.update_stats('', 'exporting scene...')
            time_export_start = time.perf_counter()
            scene_exporter = export.SceneExport(scene, scene_synced)

            # texture compression context param needs to be set before exporting textures
            pyrpr.ContextSetParameter1u(scene_renderer.get_core_context(), b"texturecompression",
                                        settings.texturecompression)

            if self.is_preview:
                is_icon = width <= 32 and height <= 32
                scene_exporter.export_preview(is_icon)
            else:
                for name in scene_exporter.export_iter():
                    if self.test_break():
                        return
                    logging.debug('exporting:', name, tag='sync')
                    self.update_stats("Exporting", str(name))
                if not self.is_preview:
                    self.report({'INFO'},
                                'RPR: scene export took {:.3f} seconds'.format(time.perf_counter() - time_export_start))

            scene_renderer_treaded = rprblender.render.scene.SceneRendererThreaded(scene_renderer)
            scene_renderer_treaded.start_noninteractive()

            if not self.is_preview:
                if rprblender.render.render_layers.use_custom_passes:
                    # Blender 2.79
                    self.add_passes(aov_settings)

            result = self.begin_result(0, 0, width, height)
            logging.debug("Passes in the result:", tag="render.engine.passes")
            # TODO: render to active layer or render all layers
            result_render_layer = result.layers[0]
            for p in result_render_layer.passes:
                logging.debug("    pass:", p.name, tag="render.engine.passes")

            render_failed = False
            try:
                iteration_displayed = None
                while True:
                    render_completed = False
                    # update render stats few times before displaying intermediate results(long operation in Blender)
                    for i in range(10):
                        if not scene_renderer_treaded.is_alive():
                            render_failed = True
                            return
                        if self.test_break():
                            return
                        self.update_scene_render_stats(self, scene_renderer, settings.rendering_limits)
                        if scene_renderer_treaded.render_completed_event.wait(timeout=0.1):
                            render_completed = True
                            break
                    if render_completed:
                        break
                    iteration = self.set_rendered_image_to_result(result_render_layer, scene_renderer, iteration_displayed)
                    if iteration is not None:
                        iteration_displayed = iteration
                        with TimedContext("update_result"):
                            self.update_result(result)

                iteration = self.set_rendered_image_to_result(result_render_layer, scene_renderer, iteration_displayed)
                assert iteration is not None
            finally:
                scene_renderer_treaded.stop()
                del scene_renderer_treaded
                if not render_failed:
                    with TimedContext("end_result"):
                        logging.debug("end_result", tag="render.engine")
                        self.end_result(result)
                else:
                    self.report_render_error('render', 'render failed')

        finally:
            del scene_exporter
            scene_synced.destroy()
            del scene_synced
            del scene_renderer

    @staticmethod
    def update_scene_render_stats(engine, scene_renderer: rprblender.render.scene.SceneRenderer, limits):
        if not scene_renderer.cache_generated:
            engine.update_progress(0)
            # while rendering first iteration Core may stall to rebuild OpenCL cache and this takes time
            engine.update_stats('initializing', "This may take a few minutes!")
            return

        iteration_in_progress = scene_renderer.iteration_in_progress or 0
        iteration_divider = scene_renderer.iteration_divider or 1
        if limits.enable:
            time_render_passed = ((time.perf_counter() - scene_renderer.time_render_start)
                                  if scene_renderer.time_render_start is not None
                                  else 0)
            if 'TIME' == limits.type:
                if limits.time != 0:
                    if scene_renderer.time_render_start is not None:
                        limit = datetime.timedelta(seconds=limits.time)

                        if 0.0 < limit.total_seconds():
                            engine.update_progress(time_render_passed / limit.total_seconds())
                            done = limit <= datetime.timedelta(seconds=int(time_render_passed))
                            engine.update_stats(
                                'Remaining: {}'.format(limit - datetime.timedelta(seconds=int(time_render_passed)))
                                if not done else 'Done',
                                "Iteration: {}".format(iteration_in_progress + 1))
                    return

            elif 'ITER' == limits.type:
                if limits.iterations > 0:
                    if 0 < limits.iterations and iteration_in_progress is not None:
                        render_progress = (iteration_in_progress + 1) * (1 / iteration_divider) / limits.iterations
                        engine.update_progress(render_progress)
                        if 0.0 < render_progress:
                            estimated_total_time = time_render_passed / render_progress
                            estimated_time_remaining = estimated_total_time * (1 - render_progress)
                        else:
                            estimated_time_remaining = 0

                        engine.update_stats(
                            'Remaining: {}'.format(datetime.timedelta(seconds=int(estimated_time_remaining))),
                            "Iteration: {}/{}".format(int((iteration_in_progress + 1) * (1 / iteration_divider)),
                                                      limits.iterations))
                    return

        # if we haven't limits
        if iteration_in_progress is not None:
            engine.update_progress(0)
            engine.update_stats('iteration: {}/-'.format(iteration_in_progress + 1), 'rendering...')

    @staticmethod
    def set_rendered_image_to_result(result_render_layer, scene_renderer, iteration_displayed):
        with TimedContext("get contiguous image"):
            if scene_renderer.get_image() is None:
                return None
            im = scene_renderer.get_image()
            iteration = scene_renderer.im_iteration
            if iteration_displayed == iteration:
                return None  # don't redisplay same image

        with TimedContext("copy image to rect"):
            res = []
            for p in result_render_layer.passes:
                pass_image = scene_renderer.get_image(p.name)
                if pass_image is None:
                    width, height = im.shape[1], im.shape[0]
                    pass_image = np.ones(height * width * p.channels, dtype=np.float32)
                else:
                    if p.channels != 4:
                        pass_image = pass_image[:, :, 0:p.channels]

                if bpy.context.scene.rpr.use_render_stamp:
                    rprblender.render.render_stamp.render_stamp(bpy.context.scene.rpr.render_stamp, bpy.context,
                                                                pass_image, scene_renderer.resolution[0],
                                                                scene_renderer.resolution[1], p.channels,
                                                                scene_renderer.iteration_in_progress,
                                                                scene_renderer.time_in_progress)

                res.append(pass_image.flatten())

        with TimedContext("set image to blender"):
            logging.debug("result_render_layer.passes.foreach_set:", len(res), tag="render.engine")
            result_render_layer.passes.foreach_set("rect", np.concatenate(res))

        return iteration

    def report_render_error(self, error_type, message):
        self.update_stats("ERROR", "Check log for details")
        self.report({'INFO'}, 'ERROR: Check log for details')
        self.error = error_type
        logging.critical('ERROR:', 'It is recommended to restart Blender\n', message, tag='render')

    def view_update(self, context):  # Update on data changes for viewport render
        logging.debug("view_update", tag='render')
        if self.error:
            return
        try:
            # cProfile.runctx("self._view_update(context)", globals(), locals(), sort='cumulative')
            self._view_update(context)
            self.tag_redraw()
        except:
            self.report_render_error('view_update', "view_update: Exception %s" % traceback.format_exc())

    @call_logger.logged
    def _view_update(self, context: bpy.types.Context):

        logging.debug('view_update', context,
                      'region_data.view_perspective:', context.region_data.view_perspective,
                      'space_data.lens:', context.space_data.lens,
                      'region_data.view_camera_zoom:', context.region_data.view_camera_zoom,
                      'region.width:', context.region.width,
                      'region.height:', context.region.height,
                      'region_data.view_matrix:', context.region_data.view_matrix, tag='render.viewport.update')

        if context.space_data not in self.viewport_renderers:
            self.update_stats("Exporting", "scene")
            self.viewportrenderer_space_data = context.space_data
            bpy.ops.rpr.view_render_start()
            self.tag_redraw()
            return

        viewport_renderer = self.viewport_renderers[context.space_data]

        if not viewport_renderer.scene_renderer_threaded.is_alive():
            self.report_render_error('view_update', "Render thread crashed")
            return

        for name in viewport_renderer.update_iter(context.scene):
            self.update_stats("Sync", name)
        self.tag_redraw()

    view_draw_get_image_fps_max = 20
    view_draw_get_image_timestamp = -1 / view_draw_get_image_fps_max

    def view_draw(self, context):  # Draw viewport render
        logging.debug("view_draw", tag='render')
        if self.error:
            return
        try:
            with TimedContext('_view_draw'):
                self._view_draw(context)
            # s = cProfile.runctx("self._view_draw(context)", globals(), locals(), sort='cumulative')

            self.tag_redraw()
        except:
            self.report_render_error('view_draw', "Exception: %s" % traceback.format_exc())

    @call_logger.logged
    def _view_draw(self, context):
        logging.debug('view_draw', context,
                      'region_data.view_perspective:', context.region_data.view_perspective,
                      'space_data.lens:', context.space_data.lens,
                      'region_data.view_camera_zoom:', context.region_data.view_camera_zoom,
                      'region.width:', context.region.width,
                      'region.height:', context.region.height,
                      'region_data.view_matrix:', context.region_data.view_matrix, tag='render.viewport.draw')

        if context.space_data not in self.viewport_renderers:
            self.tag_redraw()
            return

        viewport_renderer = self.viewport_renderers[context.space_data]  # type: ViewportRenderer

        if not viewport_renderer.scene_renderer_threaded.is_alive():
            self.report_render_error('view_draw', "Render thread crashed")
            return

        time_view_draw_start = time.perf_counter()

        render_resolution = (context.region.width, context.region.height)

        if (1 / self.view_draw_get_image_fps_max) < (time_view_draw_start - self.view_draw_get_image_timestamp):
            self.view_draw_get_image_timestamp = time_view_draw_start
            logging.debug("get_image", tag='render.viewport.draw')

            viewport_renderer.update_render_aov(bpy.context.scene.rpr.render)
            viewport_renderer.update_render_resolution(render_resolution)
            viewport_renderer.update_render_camera(
                sync.extract_viewport_render_camera(context, viewport_renderer.scene_renderer.render_settings))

            im = viewport_renderer.get_image()
            if im is not None:
                assert im.flags['C_CONTIGUOUS']
                self.im = im
            settings = bpy.context.scene.rpr.render
            self.update_scene_render_stats(self, viewport_renderer.scene_renderer, settings.rendering_limits)

            if self.im is not None:
                logging.debug("draw_image", tag='render.viewport.draw')
                # image from viewport_renderer can be older(before resolution was changed)
                # so that's why we are passing current resolution along with image itself(to scale)
                if not self.texture:
                    self.texture = viewportdraw.create_texture(self.im)
                else:
                    self.texture.update(self.im)

        if self.texture:
            zoom = viewport_renderer.scene_renderer.get_image_tile()
            viewportdraw.draw_image_texture(self.texture, render_resolution,
                                            zoom if zoom is not None else (1, 1))

    def update_script_node(self, node=None):  # Compile shader script node
        pass

    def update_render_passes(self, scene, srl):
        logging.debug("update_render_passes", tag="render.engine.passes")

        # explicintly register pass for it shows up in the Render Layers compositor node
        self._register_pass(scene, srl, 'Combined')

        render_settings = bpy.context.scene.rpr.render_preview if self.is_preview else scene.rpr.render  # type: rprblender.properties.RenderSettings
        aov_settings = rprblender.render.render_layers.extract_settings(render_settings)
        for pass_name in self.enumerate_passes(aov_settings):
            self._register_pass(scene, srl, pass_name)

    def _register_pass(self, scene, srl, pass_name):
        pass_info = rprblender.render.render_layers.pass2info[pass_name]
        logging.debug("    register_pass", pass_name, pass_info, tag="render.engine.passes")
        self.register_pass(scene, srl, pass_name, *pass_info)

    def add_passes(self, aov_settings):

        # not calling add_path on 'Combined' - it's already there and when adding it
        # somehow Blender doesn't show rendered image after renderer ended when Combined
        # is selected in the Image editor. Switching to another pass and back shows it, though

        logging.debug("add_passes", tag="render.engine.passes")
        for pass_name in self.enumerate_passes(aov_settings):
            pass_info = rprblender.render.render_layers.pass2info[pass_name]
            channels, chan_id = pass_info[0], pass_info[1]
            logging.debug("    add_pass", pass_name, pass_info, tag="render.engine.passes")
            self.add_pass(pass_name,     channels, chan_id)

    def enumerate_passes(self, aov_settings):
        # TODO: seems like we need to add_pass always, register_pass is for something else?

        passes = set()

        # leave out Combined from enumeration, see add_passes comment - calling add_pass
        # for Combined doesn't work well(in blender-2.78.0-git.528ae88-windows64)
        #passes.add('Combined')

        if aov_settings.enable:
            for i, pass_name in enumerate(aov_settings.passes_names):
                if aov_settings.passes_states[i]:
                    passes.add(rprblender.render.render_layers.aov2pass[pass_name])
        return passes