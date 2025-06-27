import bpy
from . import combine_mesh, group_settings, shape_key_split_settings, util


class TAREMIN_MESH_COMBINER_PT_Panel(bpy.types.Panel):
    bl_label = "Taremin Mesh Combiner"
    bl_region_type = "UI"
    bl_space_type = "VIEW_3D"
    bl_category = "Taremin"

    def draw(self, context):
        props = util.get_settings(context)
        layout = self.layout
        invalid_context = False

        if context.mode != "OBJECT":
            row = layout.row()
            row.label(text="オブジェクトモードにしてください")
            invalid_context = True

        if invalid_context:
            return

        row = layout.row(align=True)
        row.prop(props, "output_collection")
        row = layout.row(align=True)
        row.prop(props, "output_default_object")
        row = layout.row(align=True)
        row.prop(props, "remove_unnecessary_bones")
        row = layout.row(align=True)
        row.prop(props, "make_single_user")

        layout.separator()

        row = layout.row()
        row.prop(
            props,
            "groups_folding",
            icon="TRIA_RIGHT" if props.groups_folding else "TRIA_DOWN",
            icon_only=True,
        )
        row.label(text="Groups")

        if not props.groups_folding:
            row = layout.row()
            col = row.column()
            col.template_list(
                "TAREMIN_MESH_COMBINER_UL_GroupSettings",
                "",
                props,
                "combine_groups",
                props,
                "combine_group_index",
                type="DEFAULT",
            )
            col = row.column(align=True)
            col.operator(
                operator=group_settings.TAREMIN_MESH_COMBINER_OT_GroupSettings_Add.bl_idname,
                text="",
                icon="ADD",
            )
            col.operator(
                operator=group_settings.TAREMIN_MESH_COMBINER_OT_GroupSettings_Remove.bl_idname,
                text="",
                icon="REMOVE",
            )
            col.separator()
            col.operator(
                operator=group_settings.TAREMIN_MESH_COMBINER_OT_GroupSettings_Up.bl_idname,
                text="",
                icon="TRIA_UP",
            )
            col.operator(
                operator=group_settings.TAREMIN_MESH_COMBINER_OT_GroupSettings_Down.bl_idname,
                text="",
                icon="TRIA_DOWN",
            )

        layout.separator()

        row = layout.row()
        row.prop(
            props,
            "shape_key_split_folding",
            icon="TRIA_RIGHT" if props.shape_key_split_folding else "TRIA_DOWN",
            icon_only=True,
        )
        row.label(text="Split ShapeKey")

        if not props.shape_key_split_folding:
            row = layout.row()
            col = row.column()

            row.prop(props, "shape_key_split_axis_mode", text="Split Axis")

            row = layout.row()
            col = row.column()
            col.template_list(
                "TAREMIN_MESH_COMBINER_UL_ShapeKeySplitSettings",
                "",
                props,
                "shape_key_split",
                props,
                "shape_key_split_index",
                type="DEFAULT",
            )
            col = row.column(align=True)
            col.operator(
                operator=shape_key_split_settings.TAREMIN_MESH_COMBINER_OT_ShapeKeySplitSettings_Add.bl_idname,
                text="",
                icon="ADD",
            )
            col.operator(
                operator=shape_key_split_settings.TAREMIN_MESH_COMBINER_OT_ShapeKeySplitSettings_Remove.bl_idname,
                text="",
                icon="REMOVE",
            )
            col.separator()
            col.operator(
                operator=shape_key_split_settings.TAREMIN_MESH_COMBINER_OT_ShapeKeySplitSettings_Up.bl_idname,
                text="",
                icon="TRIA_UP",
            )
            col.operator(
                operator=shape_key_split_settings.TAREMIN_MESH_COMBINER_OT_ShapeKeySplitSettings_Down.bl_idname,
                text="",
                icon="TRIA_DOWN",
            )

        layout.separator()

        if not hasattr(bpy.types, "OBJECT_OT_apply_all_modifier"):
            box = layout.box()
            row = box.row()
            row.label(
                text="ApplyModifierアドオンがないためシェイプキーのあるオブジェクトでモディファイアの適用に失敗する可能性があります"
            )

        row = layout.row()
        col = row.row(align=True)
        col.operator(
            operator=combine_mesh.TAREMIN_MESH_COMBINER_OT_CombineMesh.bl_idname
        )


class TAREMIN_MESH_COMBINER_PT_ApplyShapeKeyPanel(bpy.types.Panel):
    bl_label = "Taremin Mesh Combiner"
    bl_idname = "TAREMIN_PT_apply_shape_key_panel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"  # 「データ」タブ (Object Data Properties)
    bl_parent_id = (
        "DATA_PT_shape_keys"  # 標準のシェイプキーパネルのサブパネルとして表示
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        # メッシュオブジェクトが選択されており、かつシェイプキーが存在する場合にのみ表示
        return obj and obj.type == "MESH" and obj.data and obj.data.shape_keys

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        active_sk = obj.active_shape_key

        # アクティブなシェイプキーが存在し、それがBasisではなく、かつ頂点グループが設定されているか確認
        is_bakeable = bool(
            active_sk is not None
            and active_sk != active_sk.relative_key
            and active_sk.vertex_group
        )

        row = layout.row()
        row.enabled = is_bakeable

        # オペレーターボタンを常に表示し、条件に応じて有効/無効を切り替える
        op = row.operator(
            "taremin.apply_shape_key_vertex_group",
            text="アクティブなシェイプキーに適用",
        )
        op.target_object = obj.name
        if active_sk:
            op.target_shape_key = active_sk.name
