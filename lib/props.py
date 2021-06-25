import bpy
from . import group_settings


class TareminMeshCombinerProps(bpy.types.PropertyGroup):
    output_collection: bpy.props.StringProperty(
        name="Output Collection", default="Combined Objects")
    output_default_object: bpy.props.StringProperty(
        name="Default Output Object", default="Combined")
    remove_unnecessary_bones: bpy.props.BoolProperty(
        name="非選択アーマチュアレイヤーのボーン削除",
        default=True,
        description="非選択状態のアーマチュアレイヤーにあるボーンの削除を行う")
    remove_empty_collection: bpy.props.BoolProperty(
        name="空のコレクションの削除",
        default=True,
        description="結合などや削除で空になったコレクションを削除する")
    groups_folding: bpy.props.BoolProperty()
    combine_groups: bpy.props.CollectionProperty(
        type=group_settings.TareminMeshCombinerGroupSettings
    )
    combine_group_index: bpy.props.IntProperty()
