import bpy
from . import util


class TAREMIN_MESH_COMBINER_UL_ShapeKeySplitSettings(bpy.types.UIList):
    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        row = layout.row()
        col = row.column(align=True)

        col.prop(item, "object", text="")

        if item.object is None:
            return

        col = row.column()
        col.prop(item, "shape_key", text="")


class TareminMeshCombinerShapeKeySplitSettings(bpy.types.PropertyGroup):
    object: bpy.props.PointerProperty(
        type=bpy.types.Object, poll=lambda self, object: object.type == "MESH"
    )

    # for EnumProperty bug
    # https://docs.blender.org/api/current/bpy.props.html#bpy.props.EnumProperty
    enums = {}

    def get_shape_key_enum(self, context):
        if self.object is None or self.object.data is None:
            return []

        self.enums[self.object.name] = retval = [
            (key_block.name, key_block.name, "")
            for key_block in self.object.data.shape_keys.key_blocks
            if key_block != key_block.relative_key  # exclude "Basis" shape key
        ]
        return retval

    shape_key: bpy.props.EnumProperty(items=get_shape_key_enum)


class TAREMIN_MESH_COMBINER_OT_ShapeKeySplitSettings_Add(bpy.types.Operator):
    bl_idname = "taremin.mesh_combiner_shape_key_split_settings_add"
    bl_label = "Remove Entry"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = util.get_settings(context)

        props.shape_key_split.add()
        props.shape_key_split_index = len(props.shape_key_split) - 1

        return {"FINISHED"}


class TAREMIN_MESH_COMBINER_OT_ShapeKeySplitSettings_Remove(bpy.types.Operator):
    bl_idname = "taremin.mesh_combiner_shape_key_split_settings_remove"
    bl_label = "Remove Entry"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = util.get_settings(context)

        props.shape_key_split.remove(props.shape_key_split_index)
        max_index = len(props.shape_key_split) - 1

        if props.shape_key_split_index > max_index:
            props.shape_key_split_index = max_index

        return {"FINISHED"}


class TAREMIN_MESH_COMBINER_OT_ShapeKeySplitSettings_Up(bpy.types.Operator):
    bl_idname = "taremin.mesh_combiner_shape_key_split_settings_up"
    bl_label = "Up Entry"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        props = util.get_settings(context)
        return len(props.shape_key_split) > 0 and props.shape_key_split_index > 0

    def execute(self, context):
        props = util.get_settings(context)
        index = props.shape_key_split_index
        props.shape_key_split.move(index, index - 1)
        props.shape_key_split_index = index - 1
        return {"FINISHED"}


class TAREMIN_MESH_COMBINER_OT_ShapeKeySplitSettings_Down(bpy.types.Operator):
    bl_idname = "taremin.mesh_combiner_shape_key_split_settings_down"
    bl_label = "Down Entry"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        props = util.get_settings(context)
        max_index = len(props.shape_key_split) - 1
        return (
            len(props.shape_key_split) > 0 and props.shape_key_split_index < max_index
        )

    def execute(self, context):
        props = util.get_settings(context)
        index = props.shape_key_split_index
        props.shape_key_split.move(index, index + 1)
        props.shape_key_split_index = index + 1

        return {"FINISHED"}
