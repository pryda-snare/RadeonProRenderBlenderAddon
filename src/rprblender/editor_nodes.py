from collections import OrderedDict

import bpy
import sys
from . import nodes
from .nodes import RPRTreeNode, RPRNodeSocketConnectorHelper
from .editor_sockets import RPRSocketValue
from . import rpraddon
from rprblender.core.nodes import log_mat
from . import logging
from bpy_extras.image_utils import load_image

def fix_path(path):
    if path.startswith('//'):
        res = bpy.path.abspath(path)
    else:
        res = os.path.realpath(path)

    return res.replace('\\', '/')


########################################################################################################################
# Output nodes
########################################################################################################################

@rpraddon.register_class
class RPRShaderNode_Output(RPRTreeNode):
    bl_idname = 'rpr_shader_node_output'
    bl_label = 'RPR Material Output'
    bl_icon = 'MATERIAL'
    bl_width_min = 120

    shader_in = 'Shader'
    volume_in = 'Volume'
    displacement_in = 'Displacement'

    def init(self, context):
        self.inputs.new('NodeSocketShader', self.shader_in)
        self.inputs.new('NodeSocketShader', self.volume_in)
        self.inputs.new('NodeSocketShader', self.displacement_in)


########################################################################################################################
# Shader nodes
########################################################################################################################
class RPRNodeType_Shader(RPRTreeNode):
    shader_out = 'Shader'
    bl_icon = 'MATERIAL'
    def init(self):
        self.outputs.new('NodeSocketShader', self.shader_out)


class RPRNodeType_Volume(RPRTreeNode):
    shader_out = 'Volume'
    bl_icon = 'MATERIAL'
    def init(self):
        self.outputs.new('NodeSocketShader', self.shader_out)


@rpraddon.register_class
class RPRShaderNode_Subsurface(RPRNodeType_Volume):
    bl_idname = 'rpr_shader_node_subsurface'
    bl_label = 'RPR Subsurface'
    bl_width_min = 170

    surface_intensity_in = 'Surface Intensity'
    subsurface_color_in = 'Subsurface Color'
    density_in = 'Density'
    scatter_color_in = 'Scatter color'
    scatter_amount_in = 'Scatter Amount'
    emission_color_in = 'Emission Color'
    scattering_direction_in = 'Scattering Direction'
    multiscatter_in = 'Multiscatter'

    def init(self, context):
        super(RPRShaderNode_Subsurface, self).init()
        self.inputs.new('rpr_socket_weight', self.surface_intensity_in)
        self.inputs.new('rpr_socket_color', self.subsurface_color_in)
        self.inputs.new('rpr_socket_color', self.emission_color_in)
        self.inputs.new('rpr_socket_color', self.scatter_color_in)
        self.inputs.new('rpr_socket_factor', self.scatter_amount_in)
        self.inputs.new('rpr_socket_factor', self.density_in)
        self.inputs.new('rpr_socket_scattering_direction', self.scattering_direction_in)
        self.inputs.new('NodeSocketBool', self.multiscatter_in)


@rpraddon.register_class
class RPRShaderNode_Volume(RPRNodeType_Volume):
    bl_idname = 'rpr_shader_node_volume'
    bl_label = 'RPR Volume'
    bl_width_min = 170

    scatter_color_in = 'Scatter color'
    transmission_color_in = 'Transmission color'
    emission_color_in = 'Emission Color'
    density_in = 'Density'
    scattering_direction_in = 'Scattering Direction'
    multiscatter_in = 'Multiscatter'

    def init(self, context):
        super(RPRShaderNode_Volume, self).init()
        self.inputs.new('rpr_socket_color', self.scatter_color_in)
        self.inputs.new('rpr_socket_color', self.transmission_color_in)
        self.inputs.new('rpr_socket_color', self.emission_color_in)
        self.inputs.new('rpr_socket_factor', self.density_in)
        self.inputs.new('rpr_socket_scattering_direction', self.scattering_direction_in)
        self.inputs.new('NodeSocketBool', self.multiscatter_in)


@rpraddon.register_class
class RPRShaderNode_Emissive(RPRNodeType_Shader):
    bl_idname = 'rpr_shader_node_emissive'
    bl_label = 'RPR Emissive'

    color_in = 'Emissive Color'
    intensity_in = 'Intensity'

    def init(self, context):
        super(RPRShaderNode_Emissive, self).init()
        input_emissive_color = self.inputs.new('rpr_socket_color', self.color_in)
        self.inputs.new('rpr_socket_factor', self.intensity_in)
        input_emissive_color.default_value = (1.0, 1.0, 1.0, 1.0)


@rpraddon.register_class
class RPRShaderNode_Diffuse(RPRNodeType_Shader):
    bl_idname = 'rpr_shader_node_diffuse'
    bl_label = 'RPR Diffuse'

    color_in = 'Diffuse Color'
    roughness_in = 'Roughness'
    normal_in = 'Normal'

    def init(self, context):
        super(RPRShaderNode_Diffuse, self).init()
        input_color = self.inputs.new('rpr_socket_color', self.color_in)
        self.inputs.new('rpr_socket_weight', self.roughness_in)
        self.inputs.new('rpr_socket_link', self.normal_in)
        input_color.default_value = (1.0, 1.0, 1.0, 1.0)


@rpraddon.register_class
class RPRShaderNode_DiffuseRefraction(RPRNodeType_Shader):
    bl_idname = 'rpr_shader_node_diffuse_refraction'
    bl_label = 'RPR Diffuse Refraction'

    color_in = 'Diffuse Color'
    normal_in = 'Normal'

    def init(self, context):
        super().init()
        input_color = self.inputs.new('rpr_socket_color', self.color_in)
        self.inputs.new('rpr_socket_link', self.normal_in)
        input_color.default_value = (1.0, 1.0, 1.0, 1.0)


@rpraddon.register_class
class RPRShaderNode_Microfacet(RPRNodeType_Shader):
    bl_idname = 'rpr_shader_node_microfacet'
    bl_label = 'RPR Microfacet'

    color_in = 'Diffuse Color'
    normal_in = 'Normal'
    roughness_in = 'Roughness'

    def init(self, context):
        super(RPRShaderNode_Microfacet, self).init()
        input_color = self.inputs.new('rpr_socket_color', self.color_in)
        self.inputs.new('rpr_socket_link', self.normal_in)
        self.inputs.new('rpr_socket_weight', self.roughness_in)
        input_color.default_value = (1.0, 1.0, 1.0, 1.0)


@rpraddon.register_class
class RPRShaderNode_MicrofacetRefraction(RPRNodeType_Shader):
    bl_idname = 'rpr_shader_node_microfacet_refraction'
    bl_label = 'RPR Microfacet Refraction'
    bl_icon = 'MATERIAL'

    color_in = 'Diffuse Color'
    normal_in = 'Normal'
    roughness_in = 'Roughness'
    ior_in = 'IOR'

    def init(self, context):
        super(RPRShaderNode_MicrofacetRefraction, self).init()
        input_color = self.inputs.new('rpr_socket_color', self.color_in)
        self.inputs.new('rpr_socket_link', self.normal_in)
        self.inputs.new('rpr_socket_weight', self.roughness_in)
        self.inputs.new('rpr_socket_ior', self.ior_in)
        input_color.default_value = (1.0, 1.0, 1.0, 1.0)


@rpraddon.register_class
class RPRShaderNode_Blend(RPRNodeType_Shader):
    bl_idname = 'rpr_shader_node_blend'
    bl_label = 'RPR Shader Blend'

    weight_in = 'Weight'
    shader1_in = 'Shader 1'
    shader2_in = 'Shader 2'

    has_thumbnail = True
    thumbnail = bpy.props.EnumProperty(items=RPRTreeNode.get_thumbnail_enum)

    def init(self, context):
        super(RPRShaderNode_Blend, self).init()
        self.inputs.new('rpr_socket_weight', self.weight_in)
        self.inputs.new('NodeSocketShader', self.shader1_in)
        self.inputs.new('NodeSocketShader', self.shader2_in)

    def draw_buttons(self, context, layout):
        self.draw_thumbnail(layout)


@rpraddon.register_class
class RPRShaderNode_OrenNayar(RPRNodeType_Shader):
    bl_idname = 'rpr_shader_node_oren_nayar'
    bl_label = 'RPR Oren Nayar'

    color_in = 'Diffuse Color'
    normal_in = 'Normal'
    roughness_in = 'Roughness'

    def init(self, context):
        super(RPRShaderNode_OrenNayar, self).init()
        input_color = self.inputs.new('rpr_socket_color', self.color_in)
        self.inputs.new('rpr_socket_link', self.normal_in)
        self.inputs.new('rpr_socket_weight', self.roughness_in)
        input_color.default_value = (1.0, 1.0, 1.0, 1.0)


@rpraddon.register_class
class RPRShaderNode_Refraction(RPRNodeType_Shader):
    bl_idname = 'rpr_shader_node_refraction'
    bl_label = 'RPR Refraction'

    color_in = 'Diffuse Color'
    normal_in = 'Normal'
    ior_in = 'IOR'

    def init(self, context):
        super(RPRShaderNode_Refraction, self).init()
        input_color = self.inputs.new('rpr_socket_color', self.color_in)
        self.inputs.new('rpr_socket_link', self.normal_in)
        self.inputs.new('rpr_socket_ior', self.ior_in)
        input_color.default_value = (1.0, 1.0, 1.0, 1.0)


@rpraddon.register_class
class RPRShaderNode_Reflection(RPRNodeType_Shader):
    bl_idname = 'rpr_shader_node_reflection'
    bl_label = 'RPR Reflection'

    color_in = 'Diffuse Color'
    normal_in = 'Normal'

    def init(self, context):
        super(RPRShaderNode_Reflection, self).init()
        input_color = self.inputs.new('rpr_socket_color', self.color_in)
        self.inputs.new('rpr_socket_link', self.normal_in)
        input_color.default_value = (1.0, 1.0, 1.0, 1.0)


@rpraddon.register_class
class RPRShaderNode_Transparent(RPRNodeType_Shader):
    bl_idname = 'rpr_shader_node_transparent'
    bl_label = 'RPR Transparent'

    color_in = 'Diffuse Color'

    def init(self, context):
        super(RPRShaderNode_Transparent, self).init()
        input_color = self.inputs.new('rpr_socket_color', self.color_in)
        input_color.default_value = (1.0, 1.0, 1.0, 1.0)


@rpraddon.register_class
class RPRShaderNode_Ward(RPRNodeType_Shader):
    bl_idname = 'rpr_shader_node_ward'
    bl_label = 'RPR Ward'

    color_in = 'Diffuse Color'
    rotation_in = 'Rotation'
    roughness_x_in = 'Roughness X'
    roughness_y_in = 'Roughness Y'
    normal_in = 'Normal'

    def init(self, context):
        super(RPRShaderNode_Ward, self).init()
        input_color = self.inputs.new('rpr_socket_color', self.color_in)
        self.inputs.new('rpr_socket_angle360', self.rotation_in)
        self.inputs.new('rpr_socket_weight', self.roughness_x_in)
        self.inputs.new('rpr_socket_weight', self.roughness_y_in)
        self.inputs.new('rpr_socket_link', self.normal_in)
        input_color.default_value = (1.0, 1.0, 1.0, 1.0)
        self.inputs[self.roughness_x_in].default_value = 0.5
        self.inputs[self.roughness_y_in].default_value = 0.5


@rpraddon.register_class
class OBJECT_OT_Button(bpy.types.Operator):
    bl_idname = "my.button"
    bl_label = "Button"

    def execute(self, context):

        return {'FINISHED'}

@rpraddon.register_class
class RPRShaderNode_Uber(RPRNodeType_Shader):
    bl_idname = 'rpr_shader_node_uber'
    bl_label = 'RPR Uber'
    bl_width_min = 190

    diffuse_color_in = 'Diffuse Color'
    diffuse_normal_in = 'Diffuse Normal'

    reflect_color_in = 'Reflect Color'
    reflect_ior_in = "Reflect IOR"
    reflect_roughness_x_in = "Reflect Roughness X"
    reflect_roughness_y_in = "Reflect Roughness Y"
    reflect_normal_in = 'Reflect Normal'

    coat_color_in = 'Coat Color'
    coat_ior_in = "Coat IOR"
    coat_normal_in = 'Coat Normal'

    refraction_level_in = 'Refraction Level'
    refraction_color_in = 'Refraction Color'
    refraction_ior_in = "Refraction IOR"
    refraction_roughness_in = "Refraction Roughness"
    refraction_normal_in = 'Refraction Normal'

    transparency_color_in = 'Transparency Color'
    transparency_level_in = "Transparency Level"

    def reflection_change(self, context):
        self.inputs[self.reflect_color_in].enabled = self.reflection
        self.inputs[self.reflect_ior_in].enabled = self.reflection
        self.inputs[self.reflect_roughness_x_in].enabled = self.reflection
        self.inputs[self.reflect_roughness_y_in].enabled = self.reflection
        self.inputs[self.reflect_normal_in].enabled = self.reflection

    def clear_coat_change(self, context):
        self.inputs[self.coat_color_in].enabled = self.clear_coat
        self.inputs[self.coat_ior_in].enabled = self.clear_coat
        self.inputs[self.coat_normal_in].enabled = self.clear_coat
        pass

    def refraction_change(self, context):
        self.inputs[self.refraction_level_in].enabled = self.refraction
        self.inputs[self.refraction_color_in].enabled = self.refraction
        self.inputs[self.refraction_ior_in].enabled = self.refraction
        self.inputs[self.refraction_roughness_in].enabled = self.refraction
        self.inputs[self.refraction_normal_in].enabled = self.refraction
        pass

    reflection = bpy.props.BoolProperty(name='Reflection', update=reflection_change)
    clear_coat = bpy.props.BoolProperty(name='Clear Coat', update=clear_coat_change)
    refraction = bpy.props.BoolProperty(name='Refraction', update=refraction_change)

    def init(self, context):
        super(RPRShaderNode_Uber, self).init()

        self.inputs.new('rpr_socket_color', self.diffuse_color_in).default_value = (1.0, 1.0, 1.0, 1.0)
        self.inputs.new('rpr_socket_color', self.reflect_color_in).default_value = (1.0, 1.0, 1.0, 1.0)
        self.inputs.new('rpr_socket_color', self.coat_color_in).default_value = (1.0, 1.0, 1.0, 1.0)
        self.inputs.new('rpr_socket_color', self.refraction_color_in).default_value = (1.0, 1.0, 1.0, 1.0)
        self.inputs.new('rpr_socket_color', self.transparency_color_in).default_value = (1.0, 1.0, 1.0, 1.0)

        self.inputs.new('rpr_socket_weight', self.transparency_level_in).default_value = 0.0
        self.inputs.new('rpr_socket_weight', self.refraction_level_in)

        self.inputs.new('rpr_socket_link', self.diffuse_normal_in)
        self.inputs.new('rpr_socket_link', self.reflect_normal_in)
        self.inputs.new('rpr_socket_link', self.coat_normal_in)
        self.inputs.new('rpr_socket_link', self.refraction_normal_in)

        self.inputs.new('rpr_socket_ior', self.reflect_ior_in)
        self.inputs.new('rpr_socket_ior', self.coat_ior_in)
        self.inputs.new('rpr_socket_ior', self.refraction_ior_in)

        self.inputs.new('rpr_socket_weight', self.reflect_roughness_x_in)
        self.inputs.new('rpr_socket_weight', self.reflect_roughness_y_in)
        self.inputs.new('rpr_socket_weight', self.refraction_roughness_in)

        self.reflection_change(context)
        self.clear_coat_change(context)
        self.refraction_change(context)

    def draw_buttons(self, context, layout):
        row = layout.column(align=True)
        row.alignment = 'EXPAND'
        row.prop(self, 'reflection', toggle=True)
        row.prop(self, 'clear_coat', toggle=True)
        row.prop(self, 'refraction', toggle=True)


########################################################################################################################
# Arithmetics nodes
########################################################################################################################
class RPRNodeType_Arithmetics(RPRTreeNode):
    value_out = 'Out'
    bl_icon = 'MATERIAL'

    def init(self):
        self.outputs.new('rpr_socket_value', self.value_out)

@rpraddon.register_class
class RPRValueNode_Blend(RPRNodeType_Arithmetics):
    bl_idname = 'rpr_arithmetics_node_value_blend'
    bl_label = 'RPR Value Blend'

    weight_in = 'Weight'
    value1_in = 'Value 1'
    value2_in = 'Value 2'

    def change_type(self, context):
        socket1 = self.inputs[self.value1_in]
        socket2 = self.inputs[self.value2_in]
        socket1.type = self.type
        socket2.type = self.type

    type = bpy.props.EnumProperty(name='Type',
                                  items=RPRSocketValue.get_value_types(),
                                  default='color', update=change_type)

    def init(self, context):
        super(RPRValueNode_Blend, self).init()
        self.inputs.new('rpr_socket_weight', self.weight_in)
        self.inputs.new('rpr_socket_value', self.value1_in)
        self.inputs.new('rpr_socket_value', self.value2_in)
        self.change_type(context)

    def draw_buttons(self, context, layout):
        layout.prop(self, 'type', expand=True)


@rpraddon.register_class
class RPRValueNode_Math(RPRNodeType_Arithmetics):
    bl_idname = 'rpr_arithmetics_node_math'
    bl_label = 'RPR Math'

    value1_in = 'Value 1'
    value2_in = 'Value 2'
    value3_in = 'Value 3'

    def change_params_type(self, context):
        self.inputs[0].type = self.type
        self.inputs[1].type = self.type
        self.inputs[2].type = self.type

    def change_op(self, context):
        el = self.op_settings[self.op]
        params = el['params']
        for i in range(0, 3):
            if i in params:
                self.inputs[i].name = params[i][0]
                self.inputs[i].enabled = True
            else:
                self.inputs[i].enabled = False

    op_settings = OrderedDict([
        ('ABS', {
            'name': 'Abs',
            'params': {
                0: ['Value'],
            },
        }),
        ('ACOS', {
            'name': 'Arccosine',
            'params': {
                0: ['Value'],
            },
        }),
        ('ADD', {
            'name': 'Add',
            'params': {
                0: ['Value 1'],
                1: ['Value 2'],
            },
        }),
        ('ASIN', {
            'name': 'Arcsine',
            'params': {
                0: ['Value'],
            },
        }),
        ('ATAN', {
            'name': 'Arctangent',
            'params': {
                0: ['Value'],
            },
        }),
        ('AVERAGE', {
            'name': 'Average',
            'params': {
                0: ['Value 1'],
                1: ['Value 2'],
            },
        }),
        ('AVERAGE_XYZ', {
            'name': 'Average XYZ',
            'params': {
                0: ['Value'],
            },
        }),
        ('COMBINE', {
            'name': 'Combine',
            'params': {
                0: ['Value 1'],
                1: ['Value 2'],
                2: ['Value 3'],
            },
        }),
        ('COS', {
            'name': 'Cosine',
            'params': {
                0: ['Value'],
            },
        }),
        ('CROSS3', {
            'name': 'Cross Product',
            'params': {
                0: ['Value 1'],
                1: ['Value 2'],
            },
        }),
        ('DOT3', {
            'name': 'Dot3 Product',
            'params': {
                0: ['Value 1'],
                1: ['Value 2'],
            },
        }),
        ('FLOOR', {
            'name': 'Floor',
            'params': {
                0: ['Value'],
            },
        }),
        ('LENGTH3', {
            'name': 'Length3',
            'params': {
                0: ['Value'],
            },
        }),
        ('MAX', {
            'name': 'Max',
            'params': {
                0: ['Value 1'],
                1: ['Value 2'],
            },
        }),
        ('MIN', {
            'name': 'Min',
            'params': {
                0: ['Value 1'],
                1: ['Value 2'],
            },
        }),
        ('MOD', {
            'name': 'Mod',
            'params': {
                0: ['Value 1'],
                1: ['Value 2'],
            },
        }),
        ('MUL', {
            'name': 'Multiply',
            'params': {
                0: ['Value 1'],
                1: ['Value 2'],
            },
        }),
        ('NORMALIZE3', {
            'name': 'Normalize',
            'params': {
                0: ['Value'],
            },
        }),
        ('POW', {
            'name': 'Pow',
            'params': {
                0: ['Value 1'],
                1: ['Value 2'],
            },
        }),
        ('SELECT_X', {
            'name': 'Select X',
            'params': {
                0: ['Value'],
            },
        }),
        ('SELECT_Y', {
            'name': 'Select Y',
            'params': {
                0: ['Value'],
            },
        }),
        ('SELECT_Z', {
            'name': 'Select Z',
            'params': {
                0: ['Value'],
            },
        }),
        ('SIN', {
            'name': 'Sine',
            'params': {
                0: ['Value'],
            },
        }),
        ('SUB', {
            'name': 'Subtract',
            'params': {
                0: ['Value 1'],
                1: ['Value 2'],
            },
        }),
        ('TAN', {
            'name': 'Tangent',
            'params': {
                0: ['Value'],
            },
        }),
        ('DIV', {
            'name': 'Divide',
            'params': {
                0: ['Value 1'],
                1: ['Value 2'],
            },
        }),
        ('DOT4', {
            'name': 'Dot4 Product',
            'params': {
                0: ['Value 1'],
                1: ['Value 2'],
            },
        }),
        ('SELECT_W', {
            'name': 'Select W',
            'params': {
                0: ['Value'],
            },
        }),
        ])

    def get_op_items(settings):
        items = []
        indices = list(settings)
        for k in sorted(settings, key=lambda k: settings[k]['name']):
            name = settings[k]['name']
            items.append((k, name, name, indices.index(k)))
        return items

    type = bpy.props.EnumProperty(name='Type',
                                  items=RPRSocketValue.get_value_types(),
                                  default='color', update=change_params_type)

    op = bpy.props.EnumProperty(name='Operation',
                                items=get_op_items(op_settings),
                                default='ADD', update=change_op)

    use_clamp = bpy.props.BoolProperty(name='Clamp',
                                description="Clamp result of the node to 0..1 range",
                                default=False)

    def init(self, context):
        super(RPRValueNode_Math, self).init()
        self.inputs.new('rpr_socket_value', self.value1_in)
        self.inputs.new('rpr_socket_value', self.value2_in)
        self.inputs.new('rpr_socket_value', self.value3_in)
        self.change_params_type(context)
        self.change_op(context)

    def draw_buttons(self, context, layout):
        layout.prop(self, 'op', text='')
        layout.prop(self, 'use_clamp')
        layout.prop(self, 'type', expand=True)

    def draw_label(self):
        el = self.op_settings[self.op]
        return self.bl_label + ' - ' + el['name']


########################################################################################################################
# Inputs nodes
########################################################################################################################
class RPRNodeType_Input(RPRTreeNode):
    value_out = 'Out'
    bl_icon = 'TEXTURE'

    def init(self):
        self.outputs.new('rpr_socket_color', self.value_out)

@rpraddon.register_class
class RPRMaterialNode_Constant(RPRNodeType_Input):
    bl_idname = 'rpr_input_node_constant'
    bl_label = 'RPR Color'

    color = bpy.props.FloatVectorProperty(name='Color', subtype='COLOR', min=0.0, max=1.0,
                                          size=4, default=(1.0, 1.0, 1.0, 1.0))
    def init(self, context):
        super(RPRMaterialNode_Constant, self).init()

    def draw_buttons(self, context, layout):
        layout.template_color_picker(self, 'color', value_slider=True)
        layout.prop(self, 'color', text='')


@rpraddon.register_class
class RPRMaterialNode_Value(RPRNodeType_Input):
    bl_idname = 'rpr_input_node_value'
    bl_label = 'RPR Value'

    def init(self, context):
        super(RPRMaterialNode_Value, self).init()

    def get_value_types():
        return (('float', "Float", "Float"),
                ('vector', "Vector", "Vector"))

    def value_to_vector4(self):
        if self.type == 'float':
            return (self.value_float, self.value_float, self.value_float, self.value_float)
        else:
            return self.value_vector4

    @staticmethod
    def is_vector4_equal(a, b):
        return list(a) == list(b)

    def update_value(self, context):
        if self.type == 'float':
            self.value_float = self.default_value[0]
        else:
            self.value_vector4 = self.default_value

    def update_default_value(self, context):
        val = self.value_to_vector4()
        self['default_value'] = val

        if self.type != 'vector':
            self['value_vector4'] = self.default_value
        if self.type == 'float':
            self['value_float'] = self.default_value[0]

    type = bpy.props.EnumProperty(
        name='Type',
        items=get_value_types(),
        default='float'
    )

    show = bpy.props.BoolProperty(name="Show/Hide", default=False)

    value_vector4 = bpy.props.FloatVectorProperty(name="Vector4", size=4,
                                                default = (0, 0, 0, 0),
                                                update=update_default_value)
    value_float = bpy.props.FloatProperty(name="Value", default=0, update=update_default_value)
    default_value = bpy.props.FloatVectorProperty(name="Vector4", size=4,
                                                default=(0, 0, 0, 0),
                                                update=update_value)

    def draw_buttons(self, context, layout):
        layout.prop(self, 'type', expand=True)
        if self.type == 'float':
            layout.prop(self, 'value_float')
        else:
            col = layout.column()
            row = col.row()
            row.label(text='Value')
            row.prop(self, 'show', text='', icon='TRIA_UP' if self.show else 'TRIA_DOWN')
            if self.show:
                col.prop(self, 'value_vector4', text='')


@rpraddon.register_class
class RPRMaterialNode_NormalMap(RPRNodeType_Input):
    bl_idname = 'rpr_input_node_normalmap'
    bl_label = 'RPR NormalMap'

    map_in = 'Map'
    scale_in = 'Scale'

    def init(self, context):
        super(RPRMaterialNode_NormalMap, self).init()
        self.inputs.new('rpr_socket_color', self.map_in)
        input_scale = self.inputs.new('rpr_socket_float', self.scale_in)
        input_scale.default_value = 1.0


@rpraddon.register_class
class RPRMaterialNode_BumpMap(RPRNodeType_Input):
    bl_idname = 'rpr_input_node_bumpmap'
    bl_label = 'RPR BumpMap'

    map_in = 'Map'
    scale_in = 'Scale'

    def init(self, context):
        super(RPRMaterialNode_BumpMap, self).init()
        self.inputs.new('rpr_socket_color', self.map_in)
        input_scale = self.inputs.new('rpr_socket_float', self.scale_in)
        input_scale.default_value = 1.0


@rpraddon.register_class
class RPRMaterialNode_Lookup(RPRNodeType_Input):
    bl_idname = 'rpr_input_node_lookup'
    bl_label = 'RPR Lookup'

    items = (('UV', "UV", "texture coordinates"),
             ('N', "Normal", "normal"),
             ('P', "Position", "world position"),
             ('INVEC', "InVec", "Incident direction"),
             ('OUTVEC', "OutVec", "Outgoing direction"))

    type = bpy.props.EnumProperty(name='Type',
                                  items=items,
                                  default='UV')

    def init(self, context):
        super(RPRMaterialNode_Lookup, self).init()

    def draw_buttons(self, context, layout):
        layout.prop(self, 'type')

    def draw_label(self):
        name = [val[1] for val in self.items if self.type == val[0]][0]
        return self.bl_label + ' - ' + name


########################################################################################################################
# Mapping nodes
########################################################################################################################
class RPRNodeType_Mapping(RPRTreeNode):
    value_out = 'Out'
    bl_icon = 'TEXTURE'

    def init(self):
        self.outputs.new('rpr_socket_transform', self.value_out)


@rpraddon.register_class
class RPRMaterialNode_Mapping(RPRNodeType_Mapping):
    bl_idname = 'rpr_mapping_node'
    bl_label = 'RPR Texture Mapping'
    bl_width_min = 195

    scale_in = 'Scale UV'
    offset_in = 'Offset UV'

    def init(self, context):
        super(RPRMaterialNode_Mapping, self).init()
        scale_uv = self.inputs.new('rpr_socket_uv', self.scale_in)
        self.inputs.new('rpr_socket_uv', self.offset_in)
        scale_uv.default_value = (1.0, 1.0)


########################################################################################################################
# Texture nodes
########################################################################################################################
class RPRNodeType_Texture(RPRTreeNode):
    value_out = 'Out'
    bl_icon = 'TEXTURE'

    def init(self):
        self.outputs.new('rpr_socket_color', self.value_out)


preview_collections = {}


@rpraddon.register_class
class RPR_OT_open_image_wrapper(bpy.types.Operator):
    bl_idname = "rpr.open_image_wrapper"
    bl_label = "Open Image"
    bl_description = "Open Image"

    relative_path = bpy.props.BoolProperty(
        name="Relative Path",
        description="Select the file relative to the blend file",
        default=False,
    )

    filepath = bpy.props.StringProperty(subtype="FILE_PATH")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        image = load_image(bpy.path.abspath(self.filepath))
        image.filepath = self.filepath

        for node in context.space_data.node_tree.nodes:
            if node.bl_idname == 'rpr_texture_node_image_map' and node.requested_load:
                node.image_name = image.name
                node.requested_load = False
                break

        return {'FINISHED'}


@rpraddon.register_class
class RPRMaterialNode_ImageMap(RPRNodeType_Texture):
    bl_idname = 'rpr_texture_node_image_map'
    bl_label = 'RPR Image Map'
    bl_width_min = 200

    mapping_in = 'Mapping'

    def generate_preview(self, context):
        name = self.name + '_' + self.id_data.name
        if name not in preview_collections:
            item = bpy.utils.previews.new()
            item.previews = ()
            item.image_name = ''
            preview_collections[name] = item

        item = preview_collections[name]
        wm = context.window_manager

        new_image_name = self.image_name
        if item.image_name == new_image_name:
            return item.previews
        else:
            item.image_name = new_image_name

        item.clear()

        enum_items = []

        if self.image_name in bpy.data.images:
            image = bpy.data.images[self.image_name]
            thumb = item.load(image.name, bpy.path.abspath(image.filepath), 'IMAGE')
            enum_items = [(image.filepath, image.name, '', thumb.icon_id, 0)]
            #self.update_thumbnail()

        item.previews = enum_items
        return item.previews

    def load_image(self, context):
        self.requested_load = True
        bpy.ops.rpr.open_image_wrapper('INVOKE_DEFAULT')
        self['open_image_button'] = False

    def update_image(self, context):
        if self.image_name in bpy.data.images:
            image = bpy.data.images[self.image_name]
            image.use_fake_user = True
            self.texturePath = image.filepath

    texturePath = bpy.props.StringProperty(name='', description='Image Map Path')
    image_name = bpy.props.StringProperty(default='', update=update_image)
    requested_load = bpy.props.BoolProperty()
    open_image_button = bpy.props.BoolProperty(name='Open', description='Open a new image', update=load_image)
    preview = bpy.props.EnumProperty(items=generate_preview)

    def init(self, context):
        super(RPRMaterialNode_ImageMap, self).init()
        self.inputs.new('rpr_socket_transform', self.mapping_in)

    def draw_buttons(self, context, layout):
        split = layout.split(align=True, percentage=0.7)
        split.prop_search(self, 'image_name', bpy.data, 'images', text='')
        split.prop(self, 'open_image_button', toggle=True, icon='FILESEL')
        layout.template_icon_view(self, 'preview', show_labels=True)

    def draw_label(self):
        if not self.image_name:
            return self.name
        return self.image_name


@rpraddon.register_class
class RPRMaterialNode_Noise2D(RPRNodeType_Texture):
    bl_idname = 'rpr_texture_node_noise2d'
    bl_label = 'RPR Noise 2D'

    mapping_in = 'Mapping'

    has_thumbnail = True
    thumbnail = bpy.props.EnumProperty(items=RPRTreeNode.get_thumbnail_enum)

    def init(self, context):
        super(RPRMaterialNode_Noise2D, self).init()
        self.inputs.new('rpr_socket_transform', self.mapping_in)

    def draw_buttons(self, context, layout):
        self.draw_thumbnail(layout)


@rpraddon.register_class
class RPRMaterialNode_Gradient(RPRNodeType_Texture):
    bl_idname = 'rpr_texture_node_gradient'
    bl_label = 'RPR Gradient'

    color1_in = "Color 1"
    color2_in = "Color 2"
    mapping_in = 'Mapping'

    has_thumbnail = True
    thumbnail = bpy.props.EnumProperty(items=RPRTreeNode.get_thumbnail_enum)

    def init(self, context):
        super(RPRMaterialNode_Gradient, self).init()
        input_color1 = self.inputs.new('rpr_socket_color', self.color1_in)
        input_color1.default_value = (0, 0, 0, 1)
        input_color2 = self.inputs.new('rpr_socket_color', self.color2_in)
        input_color2.default_value = (1, 1, 1, 1)
        self.inputs.new('rpr_socket_transform', self.mapping_in)

    def draw_buttons(self, context, layout):
        self.draw_thumbnail(layout)


@rpraddon.register_class
class RPRMaterialNode_Checker(RPRNodeType_Texture):
    bl_idname = 'rpr_texture_node_checker'
    bl_label = 'RPR Checker'

    mapping_in = 'Mapping'

    has_thumbnail = True
    thumbnail = bpy.props.EnumProperty(items=RPRTreeNode.get_thumbnail_enum)

    def init(self, context):
        super(RPRMaterialNode_Checker, self).init()
        self.inputs.new('rpr_socket_transform', self.mapping_in)

    def draw_buttons(self, context, layout):
        self.draw_thumbnail(layout)


@rpraddon.register_class
class RPRMaterialNode_Dot(RPRNodeType_Texture):
    bl_idname = 'rpr_texture_node_dot'
    bl_label = 'RPR Dot'

    mapping_in = 'Mapping'

    def init(self, context):
        super(RPRMaterialNode_Dot, self).init()
        self.inputs.new('rpr_socket_transform', self.mapping_in)


########################################################################################################################
# Fresnel nodes
########################################################################################################################
class RPRNodeType_Fresnel(RPRTreeNode):
    value_out = 'Out'
    bl_icon = 'TEXTURE'

    def init(self):
        self.outputs.new('rpr_socket_color', self.value_out)


@rpraddon.register_class
class RPRMaterialNode_FresnelSchlick(RPRNodeType_Fresnel):
    bl_idname = 'rpr_fresnel_schlick_node'
    bl_label = 'RPR Fresnel Schlick'

    reflectance_in = 'Reflectance'
    normal_in = 'Normal'
    in_vec_in = 'InVec'

    def init(self, context):
        super(RPRMaterialNode_FresnelSchlick, self).init()
        self.inputs.new('rpr_socket_weight', self.reflectance_in)
        self.inputs.new('rpr_socket_link', self.normal_in)
        self.inputs.new('rpr_socket_link', self.in_vec_in)

@rpraddon.register_class
class RPRMaterialNode_Fresnel(RPRNodeType_Fresnel):
    bl_idname = 'rpr_fresnel_node'
    bl_label = 'RPR Fresnel'

    ior_in = 'IOR'
    normal_in = 'Normal'
    in_vec_in = 'InVec'

    def init(self, context):
        super(RPRMaterialNode_Fresnel, self).init()
        self.inputs.new('rpr_socket_ior', self.ior_in)
        self.inputs.new('rpr_socket_link', self.normal_in)
        self.inputs.new('rpr_socket_link', self.in_vec_in)

########################################################################################################################
# Other nodes
########################################################################################################################

@rpraddon.register_class
class RPRShaderNode_Displacement(RPRNodeType_Shader):
    bl_idname = 'rpr_shader_node_displacement'
    bl_label = 'RPR Displacement'
    bl_width_min = 200

    map_in = 'Displacement Map'
    scale_min = bpy.props.FloatProperty(name='Scale Min', default=0)
    scale_max = bpy.props.FloatProperty(name='Scale Max', default=0)

    shader_out = 'Displacement'

    def init(self, context):
        super().init()
        self.inputs.new('rpr_socket_color', self.map_in)

    def draw_buttons(self, context, layout):
        layout.prop(self, 'scale_min')
        layout.prop(self, 'scale_max')


########################################################################################################################
# Groups support nodes
########################################################################################################################
GROUP_IO_NODE_COLOR = (0.7, 0.72, 0.6)

@rpraddon.register_class
class RPRDummySocket(bpy.types.NodeSocket):
    bl_idname = "rpr_dummy_socket"
    bl_label = "RPR Dummy Socket"

    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        return (0.6, 0.6, 0.6, 0.5)

@rpraddon.register_class
class RPRShaderGroupInputsNode(RPRNodeSocketConnectorHelper, RPRTreeNode):
    bl_idname = 'rpr_shader_node_group_input'
    bl_label = 'Group Inputs'
    bl_icon = 'MATERIAL'
    bl_width_min = 100

    def init(self, context):
        self.use_custom_color = True
        self.color = GROUP_IO_NODE_COLOR
        self.outputs.new('rpr_dummy_socket', '')
        self.node_kind = 'outputs'


@rpraddon.register_class
class RPRShaderGroupOutputsNode(RPRNodeSocketConnectorHelper, RPRTreeNode):
    bl_idname = 'rpr_shader_node_group_output'
    bl_label = 'Group Outputs'
    bl_icon = 'MATERIAL'
    bl_width_min = 100

    def init(self, context):
        self.use_custom_color = True
        self.color = GROUP_IO_NODE_COLOR
        self.inputs.new('rpr_dummy_socket', '')
        self.node_kind = 'inputs'