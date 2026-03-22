bl_info = {
    "name": "Dangle Physics",
    "author": "Paul D. Richardson and Gemini",
    "version": (1, 0),
    "blender": (5, 1, 0),
    "location": "View3D > Sidebar > Dangle Tab",
    "description": "Secondary motion for Armatures with Force Field & BVH support.",
    "category": "Animation",
}

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import math

def get_object_items(self, context):
    items = [("NONE", "None", "No object selected")]
    for obj in bpy.data.objects:
        if obj.type in {'MESH', 'EMPTY'}:
            items.append((obj.name, obj.name, f"Select {obj.name}"))
    return items

def get_bvh_from_mesh(obj, depsgraph):
    if not obj or obj.type != 'MESH': return None, None
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    mesh.transform(obj.matrix_world)
    bvh = BVHTree.FromPolygons([v.co for v in mesh.vertices], [p.vertices for p in mesh.polygons])
    return bvh, mesh

def get_phys_name(prefix, i): return f"{prefix}_Phys_{i}"
def get_targ_name(prefix, i): return f"{prefix}_Targ_{i}"

def dangle_handler(scene, depsgraph):
    global_pause = scene.dangle_global_pause
    anchors = [obj for obj in scene.objects if "_Phys_0" in obj.name]
    for master in anchors:
        prefix = master.name.split("_Phys_")[0]
        if master.get("is_baked", False): continue
        is_paused = global_pause or master.dangle_pause
        master_eval = master.evaluated_get(depsgraph)
        m_matrix = master_eval.matrix_world
        master_pos = m_matrix.to_translation()
        s = m_matrix.to_scale()
        current_avg_s = (abs(s.x) + abs(s.y) + abs(s.z)) / 3.0
        build_scale = master.get("build_scale", 1.0)
        scale_factor = current_avg_s / build_scale if build_scale != 0 else 1.0
        is_reset = scene.frame_current <= scene.frame_start or is_paused
        prev_pos = master_pos.copy()
        for i in range(1, 40):
            phys_link = scene.objects.get(get_phys_name(prefix, i))
            if not phys_link: break
            base_dist = phys_link.get("dist", 1.0)
            dist_target = base_dist * scale_factor
            local_offset = Vector(phys_link.get("pose_offset", (0, 0, -base_dist * i)))
            if is_reset:
                reset_pos = m_matrix @ local_offset
                phys_link.location = reset_pos
                phys_link["last_pos"] = reset_pos.copy()
                prev_pos = reset_pos.copy()
                continue
            fric, grav, stiff = phys_link.get("dangle_fric", 0.5), phys_link.get("dangle_grav", 0.5), phys_link.get("dangle_stiff", 0.5)
            if "last_pos" not in phys_link: phys_link["last_pos"] = phys_link.location.copy()
            curr_pos, last_pos = phys_link.location.copy(), Vector(phys_link["last_pos"])
            wind_force = Vector((0, 0, 0))
            wind_name = master.dangle_wind_enum
            wind_obj = bpy.data.objects.get(wind_name) if wind_name != "NONE" else None
            if wind_obj and wind_obj.type == 'EMPTY' and hasattr(wind_obj, "field"):
                direction = wind_obj.matrix_world.to_quaternion() @ Vector((0, 0, 1))
                flutter = math.sin(scene.frame_current * 0.5) * wind_obj.field.noise if wind_obj.field.noise > 0 else 0
                wind_force = direction * (wind_obj.field.strength + flutter) * 0.01
            velocity = ((curr_pos - last_pos) * fric) + wind_force
            gravity_vec = Vector((0, 0, -grav * scale_factor * 0.1))
            rest_target = m_matrix @ local_offset
            stiffness_vec = (rest_target - curr_pos) * (stiff * 0.1)
            next_pos = curr_pos + velocity + gravity_vec + stiffness_vec
            col_name = master.dangle_col_enum
            collider_obj = bpy.data.objects.get(col_name) if col_name != "NONE" else None
            if collider_obj:
                bvh, _ = get_bvh_from_mesh(collider_obj, depsgraph)
                if bvh:
                    loc, norm, _, d = bvh.find_nearest(next_pos)
                    if loc and d < master.dangle_col_radius:
                        next_pos = loc + (norm * master.dangle_col_radius)
            diff = next_pos - prev_pos
            if diff.length > 0: next_pos = prev_pos + (diff.normalized() * dist_target)
            phys_link.location = next_pos
            phys_link["last_pos"] = curr_pos
            prev_pos = next_pos.copy()

def unbake_chain(prefix, scene):
    anchor = scene.objects.get(get_phys_name(prefix, 0))
    if anchor: anchor["is_baked"] = False
    links = [o for o in scene.objects if o.name.startswith(prefix) and "_Phys_" in o.name]
    for emp in links:
        if emp.animation_data: emp.animation_data_clear()
    bpy.context.view_layer.update()

def bake_logic_core(prefixes, context):
    scene = context.scene
    start, end = scene.frame_start, scene.frame_end
    all_phys, anchors = [], []
    for pr in prefixes:
        unbake_chain(pr, scene)
        anchor = scene.objects.get(get_phys_name(pr, 0))
        if anchor:
            anchors.append(anchor)
            links = [o for o in scene.objects if o.name.startswith(pr) and "_Phys_" in o.name and "_Phys_0" not in o.name]
            all_phys.extend(links)
    if not all_phys: return
    for f in range(start, end + 1):
        scene.frame_set(f)
        for emp in all_phys: emp.keyframe_insert(data_path="location")
    for a in anchors: a["is_baked"] = True

class DANGLE_OT_Bake(bpy.types.Operator):
    bl_idname = "dangle.bake_chain"; bl_label = "Bake This Dangle"; prefix: bpy.props.StringProperty()
    def execute(self, context): bake_logic_core([self.prefix], context); return {'FINISHED'}

class DANGLE_OT_Unbake(bpy.types.Operator):
    bl_idname = "dangle.unbake_chain"; bl_label = "Unbake This Dangle"; prefix: bpy.props.StringProperty()
    def execute(self, context): unbake_chain(self.prefix, context.scene); return {'FINISHED'}

class DANGLE_OT_BakeAll(bpy.types.Operator):
    bl_idname = "dangle.bake_all"; bl_label = "Bake All"
    def execute(self, context):
        anchors = [obj for obj in context.scene.objects if "_Phys_0" in obj.name]
        prefixes = [a.name.split("_Phys_")[0] for a in anchors]
        if prefixes: bake_logic_core(prefixes, context)
        return {'FINISHED'}

class DANGLE_OT_UnbakeAll(bpy.types.Operator):
    bl_idname = "dangle.unbake_all"; bl_label = "Unbake All"
    def execute(self, context):
        for o in [obj for obj in context.scene.objects if "_Phys_0" in obj.name]:
            unbake_chain(o.name.split("_Phys_")[0], context.scene)
        return {'FINISHED'}

class DANGLE_OT_ApplyAll(bpy.types.Operator):
    bl_idname = "dangle.apply_all"; bl_label = "Apply to All Links"; prefix: bpy.props.StringProperty(); link_idx: bpy.props.IntProperty()
    def execute(self, context):
        src = bpy.data.objects.get(get_phys_name(self.prefix, self.link_idx))
        if not src: return {'CANCELLED'}
        f, g, s = src["dangle_fric"], src["dangle_grav"], src["dangle_stiff"]
        for i in range(1, 40):
            t = bpy.data.objects.get(get_phys_name(self.prefix, i))
            if not t: break
            t["dangle_fric"], t["dangle_grav"], t["dangle_stiff"] = f, g, s
        return {'FINISHED'}

class DANGLE_OT_Build(bpy.types.Operator):
    bl_idname = "dangle.build_stabilized"; bl_label = "Build Dangle Chain"
    def execute(self, context):
        if context.mode != 'POSE': return {'CANCELLED'}
        sel = context.selected_pose_bones; arm = context.object
        parent_col = arm.users_collection[0]
        cid = 1
        while bpy.data.collections.get(f"Dangle {cid}"): cid += 1
        prefix = f"D{cid}"
        col = bpy.data.collections.new(f"Dangle {cid}"); parent_col.children.link(col)
        anchor = bpy.data.objects.new(get_phys_name(prefix, 0), None); col.objects.link(anchor)
        anchor.location = arm.matrix_world @ sel[0].tail
        con = anchor.constraints.new('COPY_TRANSFORMS')
        con.target, con.subtarget, con.head_tail = arm, sel[0].name, 1.0
        context.view_layer.update()
        m_inv, s = anchor.matrix_world.inverted(), anchor.matrix_world.to_scale()
        anchor["build_scale"] = (abs(s.x) + abs(s.y) + abs(s.z)) / 3.0
        for i in range(1, len(sel)):
            pb = sel[i]; t_pos = arm.matrix_world @ pb.tail
            p_link = bpy.data.objects.new(get_phys_name(prefix, i), None); col.objects.link(p_link)
            p_link.location, p_link["pose_offset"] = t_pos, m_inv @ t_pos
            p_link["dist"] = (t_pos - (arm.matrix_world @ pb.head)).length
            p_link["dangle_fric"], p_link["dangle_grav"], p_link["dangle_stiff"] = 0.5, 0.5, 0.5
            t_link = bpy.data.objects.new(get_targ_name(prefix, i), None); col.objects.link(t_link)
            t_link.location = t_pos
            t_link.constraints.new('COPY_LOCATION').target = p_link
            pb.constraints.new('DAMPED_TRACK').target = t_link
        return {'FINISHED'}

class DANGLE_OT_Delete(bpy.types.Operator):
    bl_idname = "dangle.delete_chain"; bl_label = "Remove Dangle Chain"; prefix: bpy.props.StringProperty()
    def execute(self, context):
        unbake_chain(self.prefix, context.scene)
        for arm in [o for o in bpy.data.objects if o.type == 'ARMATURE']:
            for b in arm.pose.bones:
                for c in list(b.constraints):
                    if hasattr(c, "target") and c.target and c.target.name.startswith(self.prefix):
                        b.constraints.remove(c)
        for o in [o for o in bpy.data.objects if o.name.startswith(f"{self.prefix}_")]:
            bpy.data.objects.remove(o, do_unlink=True)
        col = bpy.data.collections.get(f"Dangle {self.prefix[1:]}")
        if col: bpy.data.collections.remove(col)
        return {'FINISHED'}

class DANGLE_PT_Panel(bpy.types.Panel):
    bl_label = "Dangle Physics"; bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = 'Dangle'
    def draw(self, context):
        layout, scene = self.layout, context.scene
        layout.prop(scene, "dangle_global_pause", text="Pause All Dangles", icon='PAUSE')
        layout.separator(); layout.operator("dangle.build_stabilized", icon='PHYSICS')
        active = context.active_pose_bone
        if not active: return
        
        prefix, current_link_idx = None, -1
        # SEARCH BY CONSTRAINT INSTEAD OF BONE NAME
        for a in [obj for obj in scene.objects if "_Phys_0" in obj.name]:
            c = a.constraints.get("Copy Transforms")
            if c and c.subtarget == active.name:
                prefix = a.name.split("_Phys_0")[0]
                current_link_idx = 0
                break
        if prefix is None:
            for c in active.constraints:
                if hasattr(c, 'target') and c.target and "_Targ_" in c.target.name:
                    targ_name = c.target.name
                    prefix = targ_name.split("_Targ_")[0]
                    current_link_idx = int(targ_name.split("_Targ_")[-1])
                    break

        if prefix:
            anchor = scene.objects.get(get_phys_name(prefix, 0))
            is_baked = anchor.get("is_baked", False)
            col_local = layout.column(); col_local.enabled = not scene.dangle_global_pause
            col_local.prop(anchor, "dangle_pause", text="Pause This Dangle", icon='PAUSE')
            if current_link_idx > 0:
                p_link = scene.objects.get(get_phys_name(prefix, current_link_idx))
                if p_link:
                    box = layout.box()
                    box.label(text=f"Settings: {prefix} (Link {current_link_idx})", icon='CON_TRACKTO')
                    box.enabled = not (scene.dangle_global_pause or anchor.dangle_pause or is_baked)
                    col = box.column(align=True)
                    col.prop(p_link, '["dangle_stiff"]', text="Stiffness")
                    col.prop(p_link, '["dangle_fric"]', text="Momentum")
                    col.prop(p_link, '["dangle_grav"]', text="Gravity")
                    op = box.operator("dangle.apply_all", icon='COPYDOWN'); op.prefix, op.link_idx = prefix, current_link_idx
            box_env = layout.box(); box_env.label(text="Environment", icon='FORCE_WIND')
            box_env.enabled = not is_baked
            col_env = box_env.column(align=True)
            col_env.prop(anchor, "dangle_wind_enum", text="Wind")
            col_env.prop(anchor, "dangle_col_enum", text="Collider")
            col_env.prop(anchor, "dangle_col_radius", text="Distance")
            box_bake = layout.box(); box_bake.label(text="Bake", icon='IMAGE')
            col_bk = box_bake.column(align=True)
            col_bk.operator("dangle.bake_chain", text="Bake This Dangle").prefix = prefix
            col_bk.operator("dangle.unbake_chain", text="Unbake This Dangle").prefix = prefix
            row_all = box_bake.row(align=True)
            row_all.operator("dangle.bake_all", text="Bake All"); row_all.operator("dangle.unbake_all", text="Unbake All")
            layout.separator(); layout.operator("dangle.delete_chain", text="Remove Dangle Chain", icon='X').prefix = prefix

def register():
    bpy.types.Scene.dangle_global_pause = bpy.props.BoolProperty(name="Pause All Dangles", default=False)
    bpy.types.Object.dangle_col_enum = bpy.props.EnumProperty(name="Collider", items=get_object_items)
    bpy.types.Object.dangle_wind_enum = bpy.props.EnumProperty(name="Wind", items=get_object_items)
    bpy.types.Object.dangle_col_radius = bpy.props.FloatProperty(name="Distance", default=1.0, min=0.0, max=10.0)
    bpy.types.Object.dangle_pause = bpy.props.BoolProperty(name="Pause Physics", default=False)
    bpy.utils.register_class(DANGLE_OT_ApplyAll); bpy.utils.register_class(DANGLE_OT_Build)
    bpy.utils.register_class(DANGLE_OT_Bake); bpy.utils.register_class(DANGLE_OT_Unbake)
    bpy.utils.register_class(DANGLE_OT_BakeAll); bpy.utils.register_class(DANGLE_OT_UnbakeAll)
    bpy.utils.register_class(DANGLE_OT_Delete); bpy.utils.register_class(DANGLE_PT_Panel)
    if dangle_handler not in bpy.app.handlers.frame_change_post: bpy.app.handlers.frame_change_post.append(dangle_handler)

def unregister():
    bpy.utils.unregister_class(DANGLE_OT_ApplyAll); bpy.utils.unregister_class(DANGLE_OT_Build)
    bpy.utils.unregister_class(DANGLE_OT_Bake); bpy.utils.unregister_class(DANGLE_OT_Unbake)
    bpy.utils.unregister_class(DANGLE_OT_BakeAll); bpy.utils.unregister_class(DANGLE_OT_UnbakeAll)
    bpy.utils.unregister_class(DANGLE_OT_Delete); bpy.utils.unregister_class(DANGLE_PT_Panel)
    if dangle_handler in bpy.app.handlers.frame_change_post: bpy.app.handlers.frame_change_post.remove(dangle_handler)

if __name__ == "__main__": register()
