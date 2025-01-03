import bpy
import re
import time

bl_info = {
    "name": "Tarkov Toolkit",
    "version": (1, 0, 1),
    "author": "mrsharkus12",
    "blender": (2, 93, 0),
    "location": "3D Viewport > Sidebar > Tarkov Toolkit",
    "description": "A toolkit pack for a more comfortable Tarkov asset management.",
    "category": "Development",
}

AttachmentToSlot = [
    ("reciever", "mod_reciever"),
    ("handguard", "mod_handguard"),
    ("barrel", "mod_barrel"),
    ("muzzle", "mod_muzzle"),
    ("gas_block", "mod_gas_block"),
    ("pistolgrip", "mod_pistol_grip"),
    ("pistolgrip", "mod_pistolgrip"),   # wat the fuck?
    ("charge", "mod_charge"),
    ("stock", "mod_stock"),
    ("stock", "mod_stock_000"),
    ("mag", "mod_magazine"),
    ("launcher", "mod_launcher"),
    ("scope", "mod_scope"),
    ("mount", "mod_mount"),
    ("bipod", "mod_bipod"),
    ("foregrip", "mod_foregrip"),
    ("tactical", "mod_tactical"),
    ("sight_rear", "mod_sight_rear"),
    ("sight_front", "mod_sight_front"),
    
    ("tactical_000", "mod_tactical_000"),
    ("tactical_001", "mod_tactical_001"),
    ("tactical_002", "mod_tactical_002"),
    ("tactical_003", "mod_tactical_003"),
    ("tactical_004", "mod_tactical_004"),
    ("tactical_005", "mod_tactical_005"),

    ("mount_000", "mod_mount_000"),
    ("mount_001", "mod_mount_001"),
    ("mount_002", "mod_mount_002"),
    ("mount_003", "mod_mount_003"),
    ("mount_004", "mod_mount_004"),
    ("mount_005", "mod_mount_005"),
]

EngineBonesNames = [
    "Bend_Goal_Left", 
    "Bend_Goal_Right", 
    "smokeport", 
    "weapon_L_hand_marker", 
    "weapon_L_IK_marker", 
    "weapon_LCollarbone_marker", 
    "weapon_R_hand_marker", 
    "weapon_R_IK_marker", 
    "weapon_RCollarbone_marker", 
    "weapon_vest_IK_marker", 
    "shellport", 
    "Camera_animated", 
    "Weapon_root", 
    "Weapon_root_anim", 
    "aim_camera", 
    "mod_magazine_new",
    "fireport",
    "mod_aim_camera",
    "mod_align_rear",
    "mod_align_front"
]

HumanBonesParents = [
    'Base HumanLCollarbone', 
    'Base HumanRCollarbone',
    'Base HumanLPalm', 
    'Base HumanLPalm 1', 
    'Base HumanLPalm001',
    'Base HumanRPalm', 
    'Base HumanRPalm 1', 
    'Base HumanRPalm001'
]

class OBJECT_OT_LoadMagazines(bpy.types.Operator):
    bl_idname = "object.load_tarkov_magazines"
    bl_label = "Load Magazine"
    bl_description = "Moves selected objects that ends with '.Patron.XXX' to the corresponding bone '_patron_XXX' and parents them"
    
    def execute(self, context):
        active_armature = context.active_object

        if active_armature and active_armature.type == 'ARMATURE':
            for obj in context.selected_objects:
                if obj != active_armature:
                    match = re.search(r"Patron\.(\d+)$", obj.name)
                    if match:
                        bone_name = f"patron_{match.group(1).zfill(3)}"
                        self.moveObjToBone(obj, active_armature, bone_name)
                        self.parentKeepTransform(obj, active_armature, bone_name)

            bpy.ops.object.mode_set(mode='OBJECT')
            self.report({'INFO'}, f"Magazine '{active_armature.name}' loaded.")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "No active armature selected.")
            return {'CANCELLED'}

    def moveObjToBone(self, obj, armature, bone_name):
        if armature and obj:
            context = bpy.context
            context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='POSE')

            bone = armature.pose.bones.get(bone_name)
            if bone:
                armature_matrix = armature.matrix_world
                bone_location = armature_matrix @ bone.head
                obj.location = bone_location
            else:
                self.report({'WARNING'}, f"Bone '{bone_name}' not found in armature '{armature.name}'.")

    def parentKeepTransform(self, obj, armature, bone_name):
        if obj is None or armature is None:
            self.report({'WARNING'}, "Object or Armature not found.")
            return

        if armature.type == 'ARMATURE':
            context = bpy.context
            context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='POSE')

            bone = armature.data.bones.get(bone_name)
            if bone is None:
                self.report({'WARNING'}, f"Bone '{bone_name}' not found in armature '{armature.name}'.")
                return

            world_matrix = obj.matrix_world.copy()

            obj.parent = armature
            obj.parent_type = 'BONE'
            obj.parent_bone = bone_name

            obj.matrix_world = world_matrix

class CleanLODMaterials(bpy.types.Operator):
    bl_idname = "object.remove_lod_materials"
    bl_label = "Clean Level Of Detail Materials"
    bl_description = "Removes '_LOD1', '_LOD2' and '_LOD3' materials"
    
    def __init__(self):
        self.removed_count = 0

    def execute(self, context):
        materials_to_remove = []
        MaterialLODs = ['_LOD1', '_LOD2', '_LOD3']

        for mat in bpy.data.materials:
            if any(mat.name.endswith(lod) for lod in MaterialLODs):
                materials_to_remove.append(mat.name)

        for mat_name in materials_to_remove:
            mat = bpy.data.materials.get(mat_name)
            if mat:
                bpy.data.materials.remove(mat)
                self.removed_count += 1

        self.report({'INFO'}, f'LOD: Total removed: ' + str(self.removed_count) + ' materials.')
        return {'FINISHED'}

class OBJECT_OT_CleanLODMeshes(bpy.types.Operator):
    bl_idname = "object.remove_lod_meshes"
    bl_label = "Clean Level Of Detail Meshes"
    bl_description = "Removes all possible LOD meshes"

    regex_list_lod = [".*lod(_)?[1-4].*", ".*_lod($|\.)"]
    regex_list = []

    def __init__(self):
        self.removed_count = 0
        self.removed_child_count = 0
        self.avg_time = []

    def remove_children(self, obj):
        child_count = 0
        for child in obj.children:
            child_count += 1
            child_count += self.remove_children(child)
            bpy.data.objects.remove(child, do_unlink=True)
        return child_count

    def remove(self, obj):
        time_s = time.time()

        self.removed_count += 1
        removed_child_delta = self.remove_children(obj)
        self.removed_child_count += removed_child_delta

        name_rem = obj.name
        bpy.data.objects.remove(obj, do_unlink=True)

        time_e = time.time()
        t = time_e - time_s
        if removed_child_delta == 0:
            self.avg_time.append(t)
        print(f'({self.removed_count + self.removed_child_count}) Removed {name_rem} with {removed_child_delta} children')

        if (self.removed_count) % 500 == 0:
            avg_time = sum(self.avg_time) / len(self.avg_time) if self.avg_time else 0
            self.avg_time.clear()
            avg_str = '%.4f' % avg_time
            print(f'Average time to delete: {avg_str}s per object')

            # Cleaning up the data-blocks from deleted objects to speed up the whole thing
            bpy.ops.outliner.orphans_purge(do_local_ids=True)
            bpy.context.view_layer.update()

    def execute(self, context):
        print('Checking ' + str(len(bpy.context.scene.objects)) + ' objects')

        # Loop through all objects in the scene
        for obj in bpy.context.scene.objects:
            for regex in self.regex_list:
                pattern = re.compile(regex, re.IGNORECASE | re.DOTALL)
                if obj and pattern.match(obj.name):
                    self.remove(obj)
                    break

        for obj in bpy.context.scene.objects:
            if obj.parent is None:
                continue

            for regex in self.regex_list_lod:
                pattern = re.compile(regex, re.IGNORECASE)
                if pattern.match(obj.name):
                    lod0found = False
                    for sibling in obj.parent.children:
                        if sibling == obj:
                            continue
                        if sibling.name.split('.')[0].lower().endswith('_lod0'):
                            if sibling.type != 'MESH':
                                continue
                            lod0found = True
                            break

                    if lod0found:
                        self.remove(obj)
                    break

        self.report({'INFO'}, f'LOD: Total removed: ' + str(self.removed_count) + ' objects with ' + str(self.removed_child_count) + ' children')
        return {'FINISHED'}

class OBJECT_OT_CleanShadowMeshes(bpy.types.Operator):
    bl_idname = "object.remove_shadow_meshes"
    bl_label = "Clean Shadow Meshes"
    bl_description = "Removes all possible Unity's shadow meshes"

    regex_list = [".*SHADOW.*", ".*Sten(s|c)il.*"]

    def __init__(self):
        self.removed_count = 0
        self.removed_child_count = 0
        self.avg_time = []

    def remove_children(self, obj):
        child_count = 0
        for child in obj.children:
            child_count += 1
            child_count += self.remove_children(child)
            bpy.data.objects.remove(child, do_unlink=True)
        return child_count

    def remove(self, obj):
        time_s = time.time()

        self.removed_count += 1
        removed_child_delta = self.remove_children(obj)
        self.removed_child_count += removed_child_delta

        name_rem = obj.name
        bpy.data.objects.remove(obj, do_unlink=True)

        time_e = time.time()
        t = time_e - time_s
        if removed_child_delta == 0:
            self.avg_time.append(t)
        print(f'({self.removed_count + self.removed_child_count}) Removed {name_rem} with {removed_child_delta} children')

        if (self.removed_count) % 500 == 0:
            avg_time = sum(self.avg_time) / len(self.avg_time) if self.avg_time else 0
            self.avg_time.clear()
            avg_str = '%.4f' % avg_time
            print(f'Average time to delete: {avg_str}s per object')

            # Cleaning up the data-blocks from deleted objects to speed up the whole thing
            bpy.ops.outliner.orphans_purge(do_local_ids=True)
            bpy.context.view_layer.update()

    def execute(self, context):
        print('Checking ' + str(len(bpy.context.scene.objects)) + ' objects')

        # Loop through all objects in the scene
        for obj in bpy.context.scene.objects:
            for regex in self.regex_list:
                pattern = re.compile(regex, re.IGNORECASE | re.DOTALL)
                if obj and pattern.match(obj.name):
                    self.remove(obj)
                    break

        for obj in bpy.context.scene.objects:
            if obj.parent is None:
                continue

        print('Total removed: ' + str(self.removed_count) + ' objects with ' + str(self.removed_child_count) + ' children')
        self.report({'INFO'}, f'Total removed: ' + str(self.removed_count) + ' objects with ' + str(self.removed_child_count) + ' children')
        return {'FINISHED'}

class OBJECT_OT_CleanTriggerMeshes(bpy.types.Operator):
    bl_idname = "object.remove_trigger_meshes"
    bl_label = "Clean Trigger Meshes"
    bl_description = "Removes all possible Unity's game trigger meshes"

    regex_list = [".*BLOCKER.*", "^Cube.*"]

    def __init__(self):
        self.removed_count = 0
        self.removed_child_count = 0
        self.avg_time = []

    def remove_children(self, obj):
        child_count = 0
        for child in obj.children:
            child_count += 1
            child_count += self.remove_children(child)
            bpy.data.objects.remove(child, do_unlink=True)
        return child_count

    def remove(self, obj):
        time_s = time.time()

        self.removed_count += 1
        removed_child_delta = self.remove_children(obj)
        self.removed_child_count += removed_child_delta

        name_rem = obj.name
        bpy.data.objects.remove(obj, do_unlink=True)

        time_e = time.time()
        t = time_e - time_s
        if removed_child_delta == 0:
            self.avg_time.append(t)
        print(f'({self.removed_count + self.removed_child_count}) Removed {name_rem} with {removed_child_delta} children')

        if (self.removed_count) % 500 == 0:
            avg_time = sum(self.avg_time) / len(self.avg_time) if self.avg_time else 0
            self.avg_time.clear()
            avg_str = '%.4f' % avg_time
            print(f'Average time to delete: {avg_str}s per object')

            bpy.ops.outliner.orphans_purge(do_local_ids=True)
            bpy.context.view_layer.update()

    def execute(self, context):
        print('Checking ' + str(len(bpy.context.scene.objects)) + ' objects')

        for obj in bpy.context.scene.objects:
            for regex in self.regex_list:
                pattern = re.compile(regex, re.IGNORECASE | re.DOTALL)
                if obj and pattern.match(obj.name):
                    self.remove(obj)
                    break

        for obj in bpy.context.scene.objects:
            if obj.parent is None:
                continue

        print('Total removed: ' + str(self.removed_count) + ' objects with ' + str(self.removed_child_count) + ' children')
        self.report({'INFO'}, f'Total removed: ' + str(self.removed_count) + ' objects with ' + str(self.removed_child_count) + ' children')
        return {'FINISHED'}

class OBJECT_OT_CleanDoorHandMeshes(bpy.types.Operator):
    bl_idname = "object.remove_door_hand_meshes"
    bl_label = "Clean Door Hand Points"
    bl_description = "Removes all possible hand points from EFT's doors"

    regex_list = ["^Pull\w*", "^Push\w*", ".*KeyGrip.*", ".*sg_pivot.*", ".*sg_targets.*", ".*test_hand.*", ".*HumanLPalm.*", ".*HumanRPalm.*"]

    def __init__(self):
        self.removed_count = 0
        self.removed_child_count = 0
        self.avg_time = []

    def remove_children(self, obj):
        child_count = 0
        for child in obj.children:
            child_count += 1
            child_count += self.remove_children(child)
            bpy.data.objects.remove(child, do_unlink=True)
        return child_count

    def remove(self, obj):
        time_s = time.time()

        self.removed_count += 1
        removed_child_delta = self.remove_children(obj)
        self.removed_child_count += removed_child_delta

        name_rem = obj.name
        bpy.data.objects.remove(obj, do_unlink=True)

        time_e = time.time()
        t = time_e - time_s
        if removed_child_delta == 0:
            self.avg_time.append(t)
        print(f'({self.removed_count + self.removed_child_count}) Removed {name_rem} with {removed_child_delta} children')

        if (self.removed_count) % 500 == 0:
            avg_time = sum(self.avg_time) / len(self.avg_time) if self.avg_time else 0
            self.avg_time.clear()
            avg_str = '%.4f' % avg_time
            print(f'Average time to delete: {avg_str}s per object')

            bpy.ops.outliner.orphans_purge(do_local_ids=True)
            bpy.context.view_layer.update()

    def execute(self, context):
        print('Checking ' + str(len(bpy.context.scene.objects)) + ' objects')

        for obj in bpy.context.scene.objects:
            for regex in self.regex_list:
                pattern = re.compile(regex, re.IGNORECASE | re.DOTALL)
                if obj and pattern.match(obj.name):
                    self.remove(obj)
                    break

        for obj in bpy.context.scene.objects:
            if obj.parent is None:
                continue

        self.report({'INFO'}, f'Door: Total removed: ' + str(self.removed_count) + ' objects with ' + str(self.removed_child_count) + ' children')
        return {'FINISHED'}

class OBJECT_OT_CleanCullingMeshes(bpy.types.Operator):
    bl_idname = "object.remove_culling_meshes"
    bl_label = "Clean Culling Meshes"
    bl_description = "Removes all possible game culling meshes"

    regex_list = [".*culling.*"]

    def __init__(self):
        self.removed_count = 0
        self.removed_child_count = 0
        self.avg_time = []

    def remove_children(self, obj):
        child_count = 0
        for child in obj.children:
            child_count += 1
            child_count += self.remove_children(child)
            bpy.data.objects.remove(child, do_unlink=True)
        return child_count

    def remove(self, obj):
        time_s = time.time()

        self.removed_count += 1
        removed_child_delta = self.remove_children(obj)
        self.removed_child_count += removed_child_delta

        name_rem = obj.name
        bpy.data.objects.remove(obj, do_unlink=True)

        time_e = time.time()
        t = time_e - time_s
        if removed_child_delta == 0:
            self.avg_time.append(t)
        print(f'({self.removed_count + self.removed_child_count}) Removed {name_rem} with {removed_child_delta} children')

        if (self.removed_count) % 500 == 0:
            avg_time = sum(self.avg_time) / len(self.avg_time) if self.avg_time else 0
            self.avg_time.clear()
            avg_str = '%.4f' % avg_time
            print(f'Average time to delete: {avg_str}s per object')

            bpy.ops.outliner.orphans_purge(do_local_ids=True)
            bpy.context.view_layer.update()

    def execute(self, context):
        print('Checking ' + str(len(bpy.context.scene.objects)) + ' objects')

        for obj in bpy.context.scene.objects:
            for regex in self.regex_list:
                pattern = re.compile(regex, re.IGNORECASE | re.DOTALL)
                if obj and pattern.match(obj.name):
                    self.remove(obj)
                    break

        for obj in bpy.context.scene.objects:
            if obj.parent is None:
                continue

        self.report({'INFO'}, f'Culling: Total removed: ' + str(self.removed_count) + ' objects with ' + str(self.removed_child_count) + ' children')
        return {'FINISHED'}

class OBJECT_OT_CleanColliderMeshes(bpy.types.Operator):
    bl_idname = "object.remove_collider_meshes"
    bl_label = "Clean Collision Meshes"
    bl_description = "Removes all possible collision meshes"

    regex_list = [".*BAL(L)?ISTIC.*", ".*COL(L)?IDER.*", ".*COL(L)?ISION.*", ".*LowPen.*", ".*HighPen.*"]

    def __init__(self):
        self.removed_count = 0
        self.removed_child_count = 0
        self.avg_time = []

    def remove_children(self, obj):
        child_count = 0
        for child in obj.children:
            child_count += 1
            child_count += self.remove_children(child)
            bpy.data.objects.remove(child, do_unlink=True)
        return child_count

    def remove(self, obj):
        time_s = time.time()

        self.removed_count += 1
        removed_child_delta = self.remove_children(obj)
        self.removed_child_count += removed_child_delta

        name_rem = obj.name
        bpy.data.objects.remove(obj, do_unlink=True)

        time_e = time.time()
        t = time_e - time_s
        if removed_child_delta == 0:
            self.avg_time.append(t)
        print(f'({self.removed_count + self.removed_child_count}) Removed {name_rem} with {removed_child_delta} children')

        if (self.removed_count) % 500 == 0:
            avg_time = sum(self.avg_time) / len(self.avg_time) if self.avg_time else 0
            self.avg_time.clear()
            avg_str = '%.4f' % avg_time
            print(f'Average time to delete: {avg_str}s per object')

            bpy.ops.outliner.orphans_purge(do_local_ids=True)
            bpy.context.view_layer.update()

    def execute(self, context):
        print('Checking ' + str(len(bpy.context.scene.objects)) + ' objects')

        for obj in bpy.context.scene.objects:
            for regex in self.regex_list:
                pattern = re.compile(regex, re.IGNORECASE | re.DOTALL)
                if obj and pattern.match(obj.name):
                    self.remove(obj)
                    break

        for obj in bpy.context.scene.objects:
            if obj.parent is None:
                continue

        self.report({'INFO'}, f'Colliders: Total removed: ' + str(self.removed_count) + ' objects with ' + str(self.removed_child_count) + ' children')
        return {'FINISHED'}

class OBJECT_OT_CleanHumanBones(bpy.types.Operator):
    bl_idname = "object.clean_human_bones"
    bl_label = "Clean Human Bones"
    bl_description = "Removes 'Base HumanLCollarbone' and 'Base HumanRCollarbone' and its children"

    def __init__(self):
        self.removed_count = 0
        self.removed_children_count = 0

    def execute(self, context):
        armature = context.active_object

        if armature and armature.type == 'ARMATURE':
            bpy.context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='EDIT')

            for bone_name in HumanBonesParents:
                bone = armature.data.edit_bones.get(bone_name)

                if bone:
                    for child in bone.children_recursive:
                        armature.data.edit_bones.remove(child)
                        self.removed_children_count += 1
                    armature.data.edit_bones.remove(bone)
                    self.removed_count += 1

            bpy.ops.object.mode_set(mode='OBJECT')
            self.report({'INFO'}, f'Bones: Total removed: ' + str(self.removed_count) + ' bones with ' + str(self.removed_count) + ' children')
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "No active armature found.")
            return {'CANCELLED'}

class OBJECT_OT_CleanEngineBones(bpy.types.Operator):
    bl_idname = "object.clean_engine_bones"
    bl_label = "Clean Weapon Engine Bones"
    bl_description = "Removes engine's weapon pointers in a armature"

    def __init__(self):
        self.removed_count = 0

    def execute(self, context):
        armature = context.active_object

        if armature and armature.type == 'ARMATURE':
            bpy.context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='EDIT')

            for bone_name in EngineBonesNames:
                bone = armature.data.edit_bones.get(bone_name)
                if bone:
                    armature.data.edit_bones.remove(bone)
                    self.removed_count += 1

            bpy.ops.object.mode_set(mode='OBJECT')
            self.report({'INFO'}, f'Bones: Total removed: ' + str(self.removed_count) + ' bones')
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "No active armature found.")
            return {'CANCELLED'}

class OBJECT_OT_AssemblyWeapon(bpy.types.Operator):
    bl_idname = "object.assembly_weapon"
    bl_label = "Assembly Attachments \ Weapon"
    bl_description = "Attaches selected attachments to an active attachment \ weapon."

    def move_obj_to_bone(self, obj, armature, bone_name):
        if armature and obj:
            bpy.context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='POSE')

            bone = armature.pose.bones.get(bone_name)
            if bone:
                armature_matrix = armature.matrix_world
                bone_location = armature_matrix @ bone.head
                obj.location = bone_location
            else:
                self.report({'WARNING'}, f"Bone '{bone_name}' not found in armature '{armature.name}'.")

    def parent_keep_transform(self, obj, armature, bone_name):
        if obj is None or armature is None:
            print("Object or Armature not found.")
            return

        if armature.type == 'ARMATURE':
            bpy.context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='POSE')

            bone = armature.data.bones.get(bone_name)
            if bone is None:
                print("Bone not found.")
                return

            world_matrix = obj.matrix_world.copy()

            obj.parent = armature
            obj.parent_type = 'BONE'
            obj.parent_bone = bone_name

            obj.matrix_world = world_matrix

    def execute(self, context):
        active_armature = context.active_object

        if active_armature and active_armature.type == 'ARMATURE':
            for obj in context.selected_objects:
                if obj != active_armature:
                    for object_name, bone_name in AttachmentToSlot:
                        if object_name in obj.name:
                            self.move_obj_to_bone(obj, active_armature, bone_name)
                            self.parent_keep_transform(obj, active_armature, bone_name)

            bpy.ops.object.mode_set(mode='OBJECT')
            self.report({'INFO'}, f"'{active_armature.name}' assembled.")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "No active armature selected.")
            return {'CANCELLED'}

class OBJECT_OT_CleanMuzzleFlashBones(bpy.types.Operator):
    bl_idname = "object.clean_muzzleflash_bones"
    bl_label = "Remove Muzzleflash Bones"
    bl_description = "Removes engine's muzzleflash pointers in a armature"

    def __init__(self):
        self.removed_count = 0

    def execute(self, context):
        armature = context.active_object

        if armature and armature.type == 'ARMATURE':
            bpy.context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='EDIT')

            for bone in armature.data.edit_bones[:]:
                if bone.name.startswith("muzzleflash_"):
                    armature.data.edit_bones.remove(bone)
                    self.removed_count += 1

            bpy.ops.object.mode_set(mode='OBJECT')
            self.report({'INFO'}, f'Bones: Total removed: ' + str(self.removed_count) + ' bones')
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "No active armature found.")
            return {'CANCELLED'}

class TarkovTools_Shared(bpy.types.Panel):
    bl_label = "Shared Tools"
    bl_idname = "EFT_SHARED"

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tarkov Toolkit'

    def draw(self, context):
        layout = self.layout
        
        layout.operator(CleanLODMaterials.bl_idname, icon='MATERIAL')
        layout.operator(OBJECT_OT_CleanLODMeshes.bl_idname, icon='MESH_DATA')

class TarkovTools_Weapon(bpy.types.Panel):
    bl_label = "Weapon Tools"
    bl_idname = "EFT_WEAPONS"

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tarkov Toolkit'

    def draw(self, context):
        layout = self.layout
        
        layout.operator(OBJECT_OT_LoadMagazines.bl_idname, icon='OBJECT_DATA')
        layout.operator(OBJECT_OT_AssemblyWeapon.bl_idname, icon='LINKED')
        layout.operator(OBJECT_OT_CleanHumanBones.bl_idname, icon='BONE_DATA')
        layout.operator(OBJECT_OT_CleanEngineBones.bl_idname, icon='BONE_DATA')
        layout.operator(OBJECT_OT_CleanMuzzleFlashBones.bl_idname, icon='BONE_DATA')

class TarkovTools_World(bpy.types.Panel):
    bl_label = "World Scene Tools"
    bl_idname = "EFT_WORLD"

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tarkov Toolkit'

    def draw(self, context):
        layout = self.layout
        
        layout.operator(OBJECT_OT_CleanShadowMeshes.bl_idname, icon='LIGHT')
        layout.operator(OBJECT_OT_CleanTriggerMeshes.bl_idname, icon='XRAY')
        layout.operator(OBJECT_OT_CleanCullingMeshes.bl_idname, icon='MESH_CUBE')
        layout.operator(OBJECT_OT_CleanColliderMeshes.bl_idname, icon='MESH_ICOSPHERE')
        layout.operator(OBJECT_OT_CleanDoorHandMeshes.bl_idname, icon='HAND')

def register():
    bpy.utils.register_class(OBJECT_OT_LoadMagazines)
    bpy.utils.register_class(OBJECT_OT_AssemblyWeapon)
    bpy.utils.register_class(OBJECT_OT_CleanHumanBones)
    bpy.utils.register_class(OBJECT_OT_CleanEngineBones)
    bpy.utils.register_class(OBJECT_OT_CleanMuzzleFlashBones)

    bpy.utils.register_class(CleanLODMaterials)
    bpy.utils.register_class(OBJECT_OT_CleanLODMeshes)
    bpy.utils.register_class(OBJECT_OT_CleanShadowMeshes)
    bpy.utils.register_class(OBJECT_OT_CleanTriggerMeshes)
    bpy.utils.register_class(OBJECT_OT_CleanCullingMeshes)
    bpy.utils.register_class(OBJECT_OT_CleanColliderMeshes)
    bpy.utils.register_class(OBJECT_OT_CleanDoorHandMeshes)

    bpy.utils.register_class(TarkovTools_Shared)
    bpy.utils.register_class(TarkovTools_Weapon)
    bpy.utils.register_class(TarkovTools_World)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_LoadMagazines)
    bpy.utils.unregister_class(OBJECT_OT_AssemblyWeapon)
    bpy.utils.unregister_class(OBJECT_OT_CleanHumanBones)
    bpy.utils.unregister_class(OBJECT_OT_CleanEngineBones)
    bpy.utils.unregister_class(OBJECT_OT_CleanMuzzleFlashBones)

    bpy.utils.unregister_class(CleanLODMaterials)
    bpy.utils.unregister_class(OBJECT_OT_CleanLODMeshes)
    bpy.utils.unregister_class(OBJECT_OT_CleanShadowMeshes)
    bpy.utils.unregister_class(OBJECT_OT_CleanTriggerMeshes)
    bpy.utils.unregister_class(OBJECT_OT_CleanCullingMeshes)
    bpy.utils.unregister_class(OBJECT_OT_CleanColliderMeshes)
    bpy.utils.unregister_class(OBJECT_OT_CleanDoorHandMeshes)

    bpy.utils.unregister_class(TarkovTools_Shared)
    bpy.utils.unregister_class(TarkovTools_Weapon)
    bpy.utils.unregister_class(TarkovTools_World)

if __name__ == "__main__":
    register()