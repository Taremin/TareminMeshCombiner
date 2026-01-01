import bpy
import re
import numpy

from . import util


class TAREMIN_MESH_COMBINER_OT_CombineMesh(bpy.types.Operator):
    bl_idname = "taremin.combine_mesh"
    bl_label = "結合"
    bl_description = "オブジェクトの結合と不要なオブジェクトの削除を行う"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        props = util.get_settings(context)
        meshes = []
        objects = util.get_scene_objects()
        active = objects.active

        # シェイプキーが変更されると設定された Split ShapeKey も変化するために事前に退避
        shapekey_split_settings = []
        for shape_key_split in props.shape_key_split:
            shapekey_split_settings.append(
                (shape_key_split.object, shape_key_split.shape_key)
            )

        root_layer_collection = bpy.context.view_layer.layer_collection
        dest_col = bpy.data.collections.new(props.output_collection)
        root_layer_collection.collection.children.link(dest_col)

        join_meshes = []

        def walkdown_collection(context, collection, path=[], depth=0):
            path = path + [collection]
            for obj in collection.collection.objects:
                if obj.type == "ARMATURE":
                    try:
                        dest_col.objects.link(obj)
                    except RuntimeError:
                        pass  # obj is already exists in dest_col
                if obj.type == "MESH":
                    if not util.is_hide(obj):
                        print("  " * depth + "[OBJ]" + obj.name + " - " + obj.type)

                        # Apply shape key vertex groups if enabled
                        if props.apply_shape_key_vertex_groups and obj.data.shape_keys:
                            # Ensure object is in OBJECT mode for operator calls
                            if context.mode != "OBJECT":
                                bpy.ops.object.mode_set(mode="OBJECT")

                            # Set active object and select it for the operator to work correctly
                            util.set_active_object(obj)
                            bpy.ops.object.select_all(action="DESELECT")  # Deselect all
                            util.select(obj, True)  # Select current object

                            # Iterate over a copy of key_blocks because we might remove them
                            for sk in list(obj.data.shape_keys.key_blocks):
                                # Skip Basis key and keys without a vertex group
                                if sk.name == "Basis" or not sk.vertex_group:
                                    continue
                                print(
                                    f"    Applying shape key vertex group for: {obj.name} - {sk.name}"
                                )
                                try:
                                    bpy.ops.taremin.apply_shape_key_vertex_group(
                                        target_object=obj.name, target_shape_key=sk.name
                                    )
                                except RuntimeError as e:
                                    self.report(
                                        {"WARNING"},
                                        f"Failed to apply shape key vertex group for {obj.name} - {sk.name}: {e}",
                                    )

                        self.apply_all_modifier(context, obj)

                        # 不必要な頂点グループを削除
                        if props.remove_unnecessary_vertex_groups:
                            self.remove_unnecessary_vertex_groups(obj, True)

                        join_meshes.append((obj, path))

            for child in collection.children:
                if child.hide_viewport or child.exclude:
                    pass
                else:
                    walkdown_collection(context, child, path, depth + 1)

        walkdown_collection(context, root_layer_collection)

        # join meshes
        join_dict = {}
        for obj, path in join_meshes:
            match = False
            for group in props.combine_groups:
                name = group.object_name
                if group.group_type == "COLLECTION":
                    path_names = [collection.name for collection in path]
                    if len(path_names) > 0 and group.collection.name == path_names[-1]:
                        if name not in join_dict:
                            join_dict[name] = []
                        join_dict[name].append(obj)
                        match = True
                        break
                elif group.group_type == "COLLECTION_RECURSIVE":
                    path_names = [collection.name for collection in path]
                    if group.collection.name in path_names:
                        if name not in join_dict:
                            join_dict[name] = []
                        join_dict[name].append(obj)
                        match = True
                        break
                elif group.group_type == "REGEXP":
                    pattern = re.compile(group.regexp)
                    if pattern.match(obj.name):
                        name = pattern.sub(name, obj.name)
                        if name not in join_dict:
                            join_dict[name] = []
                        join_dict[name].append(obj)
                        match = True
                        break

            # default
            if not match:
                name = props.output_default_object
                if name not in join_dict:
                    join_dict[name] = []
                join_dict[name].append(obj)

        for dest_name, meshes in join_dict.items():
            mesh = bpy.data.meshes.new(dest_name)
            dest_obj = bpy.data.objects.new(name=dest_name, object_data=mesh)

            # add to scene
            dest_col.objects.link(dest_obj)

            # add armature modifier
            for target in self.get_armature_modifier_targets(meshes):
                modifier = dest_obj.modifiers.new(name="Armature", type="ARMATURE")
                modifier.object = bpy.data.objects[target]

            print("JOIN:", dest_obj, meshes)
            self.join_mesh(dest_obj, meshes)

            # split shapekey
            shape_keys = set()
            for obj, shape_key in shapekey_split_settings:
                if obj in meshes:
                    shape_keys.add(shape_key)
            for shape_key in shape_keys:
                self.split_shape_key(context, dest_obj, shape_key)

        # remove all collections without destination collection
        for layer_collection in root_layer_collection.children:
            if layer_collection.collection is not dest_col:
                root_layer_collection.collection.children.unlink(
                    layer_collection.collection
                )
        for obj in root_layer_collection.collection.objects:
            root_layer_collection.collection.objects.unlink(obj)

        #
        # "Merge." から始まる頂点グループの重複頂点の削除で結合する
        #
        print("Merge vertex group")
        bpy.ops.object.select_all(action="DESELECT")
        vg_pattern = re.compile(r"^Merge\.")
        for obj in util.get_scene_objects():
            print("Mesh: {} ({})".format(obj.name, obj.type))
            if obj.type not in "MESH":
                continue
            for idx in range(0, len(obj.vertex_groups)):
                vg = obj.vertex_groups[idx]
                if vg_pattern.search(vg.name):
                    util.select(obj, True)
                    bpy.ops.object.mode_set(mode="EDIT")

                    print("Merge mesh: {}".format(vg.name))
                    bpy.ops.mesh.select_all(action="DESELECT")
                    obj.vertex_groups.active_index = vg.index
                    bpy.ops.object.vertex_group_select()
                    bpy.ops.mesh.remove_doubles(threshold=0.0)

                    bpy.ops.object.mode_set(mode="OBJECT")

            if props.remove_unnecessary_vertex_groups:
                self.remove_unnecessary_vertex_groups(obj, False)

        #
        # 非選択アーマチュアレイヤーのボーンを削除
        #
        if props.remove_unnecessary_bones:
            print("Delete all unselected armature layer bones")
            removed_bones = []
            for armature in bpy.data.objects:
                if armature.type != "ARMATURE":
                    continue

                if util.is_hide(armature):
                    util.set_hide(armature, False)
                print("Armature: {}".format(armature.name))
                util.select(armature, True)
                bpy.ops.object.mode_set(mode="EDIT")

                def get_bone_visibility(armature, bone):
                    # Legacy
                    if hasattr(bone, "layers"):
                        for index in range(len(bone.layers)):
                            if armature.data.layers[index] and bone.layers[index]:
                                return True
                        return False
                    # Blender 4.0+
                    if hasattr(bone, "collections"):
                        for bone_collection in bone.collections:
                            if bone_collection.is_visible:
                                return True
                        return False
                    raise Exception("Unsupported Blender Version")

                # 非選択アーマチュアレイヤーのボーンを削除
                for bone in armature.data.edit_bones:
                    visible = get_bone_visibility(armature, bone)
                    if not visible:
                        print("\t{} - Delete Bone".format(bone.name))

                        # Legacy
                        # 非表示ではボーンの操作ができない可能性があるため念のためレイヤーを表示しているが不要かもしれない
                        if hasattr(bone, "layers"):
                            for bone_layer_index in range(len(bone.layers)):
                                bone.layers[bone_layer_index] = True

                        bone.hide = False
                        bone.select = True

                        if bone.parent:
                            removed_bones.append([bone.name, bone.parent.name])

                        armature.data.edit_bones.remove(bone)
                bpy.ops.object.mode_set(mode="OBJECT")

            # 削除したボーンの頂点ウェイトを親に加算していく
            for obj in scene.objects:
                if obj.type not in "MESH":
                    continue

                for child, parent in removed_bones:
                    if obj.vertex_groups.get(child) and obj.vertex_groups.get(parent):
                        print("Dissolve: {} -> {}".format(child, parent))
                        util.set_active_object(obj)
                        self.dissolve(
                            obj,
                            obj.vertex_groups.get(child),
                            obj.vertex_groups.get(parent),
                        )

        if props.remove_empty_collection:
            self.remove_empty_collection(scene)

        # restore shapekey settings
        props.shape_key_split.clear()
        for obj, shape_key in shapekey_split_settings:
            tmp = props.shape_key_split.add()
            tmp.object = obj
            tmp.shape_key = shape_key

        # active
        if active in meshes:
            bpy.ops.object.select_all(action="DESELECT")
            # select(active, True)

        return {"FINISHED"}

    def join_mesh(self, active, meshes):
        print("Join all mesh objects")
        auto_smooth = False
        material_set = set()
        for obj in meshes:
            bpy.ops.object.select_all(action="DESELECT")
            print("\t{} - Join".format(obj.name))
            util.select(obj, True)
            material_set.update([slot.name for slot in obj.material_slots])
            if (
                obj.data.has_custom_normals
                and hasattr(obj.data, "use_auto_smooth")
                and obj.data.use_auto_smooth
            ):
                auto_smooth = True
            util.select(active, True)
            bpy.ops.object.join()

        for i, slot in reversed(list(enumerate(active.data.materials))):
            if (slot is not None) and (slot.name in material_set):
                continue
            active.data.materials.pop(index=i)

        if auto_smooth and hasattr(active.data, "use_auto_smooth"):
            active.data.use_auto_smooth = True

    def apply_all_modifier(self, context, obj):
        props = util.get_settings(context)
        bpy.ops.object.select_all(action="DESELECT")
        util.select(obj, True)
        print("{} - {} ({})".format(obj.name, obj.type, util.is_hide(obj)))
        if props.make_single_user:
            bpy.ops.object.make_single_user(
                type="SELECTED_OBJECTS",
                object=True,
                obdata=True,
                material=False,
                animation=False,
            )
        if obj.data.shape_keys and hasattr(bpy.types, "OBJECT_OT_apply_all_modifier"):
            for mod in obj.modifiers:
                if mod.type in "ARMATURE":
                    mod.show_viewport = False
            print("\t{} - All apply".format(obj.name))
            bpy.ops.object.apply_all_modifier()
            for mod in obj.modifiers:
                if mod.type in "ARMATURE":
                    mod.show_viewport = True
        else:
            for mod in obj.modifiers:
                if mod.type not in "ARMATURE":
                    print("\t{} - Apply".format(mod.type))
                    bpy.ops.object.modifier_apply(modifier=mod.name)
                else:
                    print("\t{} - Skip".format(mod.type))

    def get_armature_modifier_targets(self, mesh_objects):
        modifier_targets = set([])
        for obj in mesh_objects:
            for modifier in obj.modifiers:
                if modifier.type in "ARMATURE":
                    modifier_targets.add(modifier.object.name)
        return modifier_targets

    def remove_empty_collection(self, scene):
        print("Delete all empty collection")
        for collection in scene.collection.children:
            if not collection.objects:
                scene.collection.children.unlink(collection)

    def dissolve(self, obj, child_vertex_group, parent_vertex_group):
        selected = numpy.zeros(len(obj.data.vertices), dtype=bool)

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.vertex_group_set_active(group=child_vertex_group.name)
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.mode_set(mode="OBJECT")

        obj.data.vertices.foreach_get("select", selected)

        for v in numpy.array(obj.data.vertices)[selected]:
            vi = [v.index]
            parent_vertex_group.add(vi, child_vertex_group.weight(v.index), "ADD")
            child_vertex_group.remove(vi)

    def remove_hidden_collection(self, context, parent):
        print("Delete all hidden collection")
        for collection in parent.children:
            if collection.hide_viewport or collection.exclude:
                print(
                    "\t{} - Delete Collection from {}".format(
                        collection.name, parent.name
                    )
                )
                parent.collection.children.unlink(collection.collection)
            else:
                self.remove_hidden_collection(context, collection)

    def create_split_shape_key(self, obj, name, points, where_result):
        split = obj.shape_key_add(name=name, from_mix=False)
        spoints = numpy.empty((len(split.points), 3), dtype=numpy.float32)
        split.points.foreach_get("co", spoints.ravel())

        spoints[where_result] = points[where_result]

        split.points.foreach_set("co", spoints.ravel())
        split.value = 0.0

        return split

    def split_shape_key(self, context, obj, shape_key_name):
        mesh = obj.data
        props = util.get_settings(context)

        key_blocks = mesh.shape_keys.key_blocks
        shape_key = key_blocks[shape_key_name]
        shape_key_basis = shape_key.relative_key

        if shape_key == shape_key_basis:
            raise ValueError("Can't split basis shape key")

        basis = numpy.empty((len(shape_key_basis.points), 3), dtype=numpy.float32)
        shape_key_basis.points.foreach_get("co", basis.ravel())

        points = numpy.empty((len(shape_key.points), 3), dtype=numpy.float32)
        shape_key.points.foreach_get("co", points.ravel())

        left, right = props.left_right_axis[props.shape_key_split_axis_mode](basis)

        self.create_split_shape_key(obj, shape_key.name + ".L", points, left)
        self.create_split_shape_key(obj, shape_key.name + ".R", points, right)

    def is_deform_bone(self, armature, vertex_group_name):
        bone = armature.data.bones.get(vertex_group_name)
        if bone and bone.use_deform:
            return True
        return False
    
    def remove_unnecessary_vertex_groups(self, obj, exclude_merge_groups):
        vg_pattern = re.compile(r"^Merge\.") # tmp, 同じパターンがあるのであとで纏める
        for target in self.get_armature_modifier_targets([obj]):
            armature = bpy.data.objects[target]

            for i, vg in reversed(list(enumerate(obj.vertex_groups))):
                if exclude_merge_groups and vg_pattern.search(vg.name):
                    continue
                if self.is_deform_bone(armature, vg.name):
                    continue
                obj.vertex_groups.remove(vg)

class TAREMIN_MESH_COMBINER_OT_ApplyShapeKeyVertexGroup(bpy.types.Operator):
    bl_idname = "taremin.apply_shape_key_vertex_group"
    bl_label = "シェイプキーの頂点グループを適用"
    bl_description = "指定されたシェイプキーの変形を、頂点グループのウェイトに基づいてシェイプキー自体に適用します"
    bl_options = {"REGISTER", "UNDO"}

    target_object: bpy.props.StringProperty(name="Object")
    target_shape_key: bpy.props.StringProperty(name="シェイプキー")

    def execute(self, context):
        obj = bpy.data.objects.get(self.target_object)
        shape_key_name = self.target_shape_key

        if not obj or not obj.data or not obj.data.shape_keys:
            self.report(
                {"ERROR"}, "有効なオブジェクトまたはシェイプキーが選択されていません。"
            )
            return {"CANCELLED"}

        basis_key = obj.data.shape_keys.key_blocks.get("Basis")
        if not basis_key:
            self.report({"ERROR"}, "Basisシェイプキーが見つかりません。")
            return {"CANCELLED"}

        target_key_block = obj.data.shape_keys.key_blocks.get(shape_key_name)
        if not target_key_block or target_key_block == basis_key:
            self.report({"ERROR"}, "有効なシェイプキーが選択されていません。")
            return {"CANCELLED"}

        vg_name = target_key_block.vertex_group
        if not vg_name:
            self.report(
                {"ERROR"}, "選択されたシェイプキーに頂点グループが設定されていません。"
            )
            return {"CANCELLED"}

        vg = obj.vertex_groups.get(vg_name)
        if not vg:
            self.report(
                {"ERROR"},
                "指定された頂点グループ '{}' がオブジェクトに見つかりません。".format(
                    vg_name
                ),
            )
            return {"CANCELLED"}

        # Ensure object is in OBJECT mode for data access
        if obj.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        # Get Basis shape key points
        basis_coords = numpy.empty(len(basis_key.points) * 3, dtype=numpy.float32)
        basis_key.points.foreach_get("co", basis_coords)
        basis_coords = basis_coords.reshape(-1, 3)

        # Get the target shape key's own point data.
        sk_points = numpy.empty(len(target_key_block.points) * 3, dtype=numpy.float32)
        target_key_block.points.foreach_get("co", sk_points)
        sk_points = sk_points.reshape(-1, 3)

        # Calculate the delta from Basis for this shape key
        deltas = sk_points - basis_coords

        # Apply the deltas to the Basis coordinates, masked by vertex group weights
        for v_idx in range(len(obj.data.vertices)):
            # Check if the vertex belongs to the vertex group and get its weight
            weight = 0.0
            for g in obj.data.vertices[v_idx].groups:
                if g.group == vg.index:
                    weight = g.weight
                    break
            if weight > 0:
                basis_coords[v_idx] += deltas[v_idx] * weight

        # Update the Basis shape key with the baked deformations
        # basis_key.points.foreach_set("co", basis_coords.ravel())

        # After baking, reset the shape key's value to 0.0 and clear its vertex group
        target_key_block.value = 0.0
        target_key_block.vertex_group = (
            ""  # Clear the vertex group as its effect is now baked
        )

        target_key_block.points.foreach_set("co", basis_coords.ravel())

        self.report(
            {"INFO"},
            "シェイプキー '{}' に頂点グループを適用しました。".format(shape_key_name),
        )
        return {"FINISHED"}
