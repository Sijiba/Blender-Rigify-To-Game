import bpy

# About This Script:
# I made a character with a Multiresolution modifier, slapped it in Rigify, and
# added a bunch of shape keys. 99 times out of 100, this is the worst
# combination of things you can possibly do if you want to be able to use the
# character in other software like Unity, due to a plethora of factors regarding
# Blender limitations. Usually such unfortunate souls have their work undone after
# discovering these limitations the hard way. Unlike them, however, you have this script.
#
# This script gives you the power to turn your cool Rigify rig into
# something you can actually use in games. This script:
#  * Creates an easier-to-export duplicate of your Rigify character
#  * Fixes vertex groups of parts that auto-rigging shouldn't deform
#  * Removes "DEF-" from all the vertex weights so the copied Metarig's bones can shine
#  * Removes a list of excess bones and transfers their mesh weights to proper parents
#  * Applies the Multiresolution modifier at its current LOD and keeps all your shapekeys
#       (this part takes a hot minute)

# Instructions:
# 1) Fill out the parameters in this section below. Change the strings and
# array contents however you need.
# 2) Run the script!
# 3) If you have any other loose parts to join to the output mesh, do that

# PARAMETERS

## CHARACTER ORIGINAL BONES AND SKINS
# Fill "metarig_name" with the original metarig armature's name.
# Fill "rigify_mesh_names" with the meshes linked to your working Rigify rig.
# All these objects will be copied, and the copied meshes will be merged together and
# parented to the copied metarig.
metarig_name = "metarig"
rigify_mesh_names = ["character.base", "character.Teeth"]

## CHARACTER OUTPUT NAMES
# Fill these in with the desired names of the output armature and mesh.
output_rig_name = "exportRig"
output_mesh_name = "exportBody"

## FIX RIGID VERTEX GROUPS
# If your character has parts that shouldn't deform (e.g. teeth), give those
# parts special vertex groups, and fill in their names in "vertex_groups_to_fix".
# They should stick if you re-weight the rest of the mesh.
# Fill "vertex_groups_goals" in the same order with the groups those vertices should
# be reassigned to.
vertex_groups_to_fix = ['FIXED-teeth.T', 'FIXED-teeth.B']
vertex_groups_goals = ['teeth.T', 'teeth.B']

## SKELETON CLEANING
# For bones YOU ADDED to the metarig outside the regular Rigify rig that you don't
# want to animate later, add their names here and they'll be cleaned up. They'll be added to
# an already existing list of regular Rigify bones to remove, defined further down.
# "custom_parents_to_clean": bones to keep, but that dont need their children
custom_parents_to_clean = []
# "custom_bones_to_remove": bones to be removed with their children
custom_bones_to_remove = []
# "custom_double_bones": mirrored bones to be re-fused after Rigify split them, akin to arms
# and legs. Give their names without the .L or .R
custom_double_bones = []

## APPLY SHAPEKEYS
# This part of the task takes a while so I'll give you the opportunity to
# turn it off if you don't use shapekeys
should_apply_multires_shapekeys = True
# set what LOD you want to output
desired_multires_level = 1

# THAT'S ALL THE PARAMETERS, NOW ONTO CODE
# constants
bones_new_parent = 'face'
multires_mod_name = "Multires"
armature_mod_name = "Armature"
lr = ["L", "R"]
tb = ['T', 'B']
# containers for armature data
parents_to_clean = []
bones_to_remove = []
bones_to_reparent = []
double_bones = []
# the active object
arm = None
obj = bpy.data.objects[rigify_mesh_names[0]]
collection = obj.users_collection[0]


def setup_data():
    global parents_to_clean, bones_to_remove, bones_to_reparent, double_bones
    # make the excess bones data
    double_bones = ['upper_arm', 'forearm', 'thigh', 'shin']

    parents_to_clean = ['jaw_master', 'nose_master']
    bones_to_remove = ['teeth.T', 'nose', 'nose.004']
    bones_to_remove += list(filter(lambda name: "glue" in name, arm.bones.keys()))

    for side in lr:
        bones_to_remove.append(f'temple.{side}')
        bones_to_remove.append(f'forehead.{side}')
        bones_to_remove.append(f'heel.02.{side}')
        bones_to_reparent.append(f'lip.T.{side}')
        bones_to_remove.append(f'lip.T.{side}')
        for height in tb:
            bones_to_remove.append(f'cheek.{height}.{side}')
            bones_to_remove.append(f'brow.{height}.{side}')
            bones_to_reparent.append(f'lid.{height}.{side}')
        for i in range(4):
            parents_to_clean.append(f'toe.{side}')
            for height in tb:
                bones_to_remove.append(f'brow.{height}.{side}.00{i + 1}')
                bones_to_remove.append(f'forehead.{side}.00{i + 1}')
        parents_to_clean.append(f'ear.{side}.001')


def fix_teeth(use_meta=True):
    to_replace = vertex_groups_to_fix
    goal_groups = vertex_groups_goals

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")

    for i in range(len(to_replace)):
        orig = to_replace[i]
        target = goal_groups[i]
        bpy.ops.object.vertex_group_set_active(group=orig)
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_remove_from(use_all_groups=True)
        bpy.ops.object.vertex_group_assign()
        bpy.ops.object.vertex_group_set_active(group=target)
        bpy.ops.object.vertex_group_assign()
        bpy.ops.object.vertex_group_deselect()

    bpy.ops.object.mode_set(mode="OBJECT")


def rename_def_weights():
    for group in obj.vertex_groups:
        if "DEF-" in group.name:
            group.name = group.name[4:]


def reparent_facebones():
    new_parent = arm.edit_bones.get(bones_new_parent)
    for bone_name in bones_to_reparent:
        bone = arm.edit_bones.get(bone_name)
        if bone:
            bone.parent = new_parent


def transfer_weights(source, target):
    source_group = obj.vertex_groups.get(source.name)
    if source_group is None:
        return
    source_i = source_group.index
    target_group = obj.vertex_groups.get(target.name)
    if target_group is None:
        target_group = obj.vertex_groups.new(name=target.name)

    for v in obj.data.vertices:
        for g in v.groups:
            if g.group == source_i:
                target_group.add((v.index,), g.weight, 'ADD')
    obj.vertex_groups.remove(source_group)


def remove_bone(source, target):
    transfer_weights(source, target)
    if (source.name in arm.edit_bones):
        edit_bone = arm.edit_bones.get(source.name)
        arm.edit_bones.remove(edit_bone)


def remove_bones(bone_names):
    for name in bone_names:
        if name in arm.bones:
            src = arm.bones[name]
            targ = arm.bones[src.parent.name]
            for bone in src.children_recursive:
                remove_bone(bone, targ)
            remove_bone(src, targ)


def remove_children(bone_names):
    for name in bone_names:
        if name in arm.bones:
            src = arm.bones[name]
            for bone in src.children_recursive:
                remove_bone(bone, src)
            # remove_bone(src, targ)


def extrabone_reweight():
    for name in double_bones:
        for side in lr:
            child_name = f'{name}.{side}.001'
            child_group = obj.vertex_groups.get(child_name)
            if child_group:
                main_name = f'{name}.{side}'
                main_group = obj.vertex_groups.get(main_name)
                transfer_weights(child_group, main_group)


def dupe_object(objec):
    dupe = objec.copy()
    dupe.data = dupe.data.copy()  # linked = False
    collection.objects.link(dupe)
    return dupe


def set_active(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def apply_multires_to_shapekeys():
    for ob in bpy.context.selected_objects:
        ob_name = ob.name

        bpy.context.object.active_shape_key_index = 0
        dupe = dupe_object(ob)
        set_active(dupe)

        # delete the copy's shape keys
        dupe.shape_key_clear()
        # apply any multires modifiers
        bpy.ops.object.modifier_apply(modifier=multires_mod_name)
        # iterate through main object's shape keys

        shapekeys = ob.data.shape_keys.key_blocks
        for index, keydata in enumerate(shapekeys):
            key = keydata.name
            if "Basis" in key:
                continue
            ## copy the mesh again, set the specified shapekey to 1
            copy2 = dupe_object(ob)
            copy2.data.shape_keys.key_blocks[key].value = 1
            set_active(copy2)
            ## do "Apply All Shape Keys"
            bpy.context.object.active_shape_key_index = index
            bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
            ## apply copy's multires modifier
            bpy.ops.object.modifier_apply(modifier=multires_mod_name)
            ## go to the target copy
            bpy.context.view_layer.objects.active = dupe
            ## Do "Join as Shapes" from iterative copy to target copy
            bpy.ops.object.join_shapes()
            ## Rename the new shapekey to the main object's correct one
            dupe.data.shape_keys.key_blocks[index].name = key
            ## Set that new key's weight to 0
            set_active(copy2)
            bpy.ops.object.delete()

        set_active(ob)
        ob.shape_key_clear()
        bpy.ops.object.modifier_apply(modifier=multires_mod_name)
        ob.data = dupe.data.copy()
        set_active(dupe)
        bpy.ops.object.delete()
        set_active(ob)


def convert_main():
    global obj, arm
    # Be in object mode please

    # Copy armature and mesh parts, set up data

    # copy the armature
    arma = bpy.data.objects[metarig_name]
    set_active(arma)
    arma = dupe_object(arma)
    arma.name = output_rig_name
    arma.data.name = output_rig_name
    arm = bpy.data.armatures[arma.data.name]

    # Copy Rigify mesh parts and join them
    obj = bpy.data.objects[rigify_mesh_names[0]]
    set_active(obj)
    obj = dupe_object(obj)
    obj.name = output_mesh_name
    set_active(obj)
    for i in range(1, len(rigify_mesh_names)):
        anotherdupe = dupe_object(bpy.data.objects[rigify_mesh_names[i]])
        anotherdupe.select_set(True)
        bpy.ops.object.join()

    setup_data()

    # with obj being the new mesh, fix teeth and rename mesh weights
    rename_def_weights()
    fix_teeth()

    # enter edit mode on armature, select all bones
    set_active(arma)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.armature.select_all(action="SELECT")
    # With "arm" as the new armature's data and "obj" as the joined mesh,
    # reparent face bones
    reparent_facebones()
    # commit that, then get back to edit mode
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.mode_set(mode="EDIT")

    # do armature operations:
    remove_children(parents_to_clean)
    remove_bones(bones_to_remove)
    extrabone_reweight()

    bpy.ops.object.mode_set(mode="OBJECT")

    # parent armature

    set_active(arma)
    obj.select_set(True)
    bpy.ops.object.parent_set()
    set_active(obj)
    obj.modifiers[armature_mod_name].object = arma

    # If we're doing multires shape keys, make obj active again and do it
    if should_apply_multires_shapekeys:
        obj.modifiers[multires_mod_name].levels = desired_multires_level
        obj.modifiers[multires_mod_name].render_levels = desired_multires_level
        obj.modifiers[multires_mod_name].sculpt_levels = desired_multires_level
        apply_multires_to_shapekeys()
    # //parent new mesh to new armature


convert_main()