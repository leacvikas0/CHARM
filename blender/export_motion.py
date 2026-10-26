"""Blender -b character.blend -P export_motion.py -- --armature NAME --output clip.npz"""
from pathlib import Path
import argparse,json,sys
import bpy,numpy as np

def main():
    p=argparse.ArgumentParser();p.add_argument('--armature',required=True);p.add_argument('--output',required=True);p.add_argument('--start',type=int);p.add_argument('--end',type=int);args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    output=Path(args.output).resolve()
    if output.exists():raise FileExistsError(output)
    scene=bpy.context.scene;arm=bpy.data.objects.get(args.armature)
    if arm is None or arm.type!='ARMATURE':raise ValueError('Named armature does not exist')
    names=[]
    def visit(bone):
        names.append(bone.name)
        for child in sorted(bone.children,key=lambda x:x.name):visit(child)
    for bone in sorted([b for b in arm.data.bones if b.parent is None],key=lambda b:b.name):visit(bone)
    lookup={n:i for i,n in enumerate(names)};parents=np.array([lookup[arm.data.bones[n].parent.name] if arm.data.bones[n].parent else -1 for n in names],dtype=np.int64)
    first=scene.frame_start if args.start is None else args.start;last=scene.frame_end if args.end is None else args.end
    if last-first<1:raise ValueError('Export at least two frames')
    scene.frame_set(first);bpy.context.view_layer.update();rest=np.array([arm.matrix_world@arm.data.bones[n].matrix_local for n in names],dtype=float)
    worlds=[]
    for frame in range(first,last+1):
        scene.frame_set(frame);bpy.context.view_layer.update();evaluated=arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
        worlds.append(np.array([evaluated.matrix_world@evaluated.pose.bones[n].matrix for n in names],dtype=float))
    output.parent.mkdir(parents=True,exist_ok=True);fps=scene.render.fps/scene.render.fps_base
    np.savez_compressed(output,world=np.array(worlds),names=np.array(names),parents=parents,rest=rest,fps=np.array(fps))
    output.with_suffix('.export.json').write_text(json.dumps({'source_blend':bpy.data.filepath,'armature':arm.name,'source_frame_start':first,'source_frame_end':last,'fps':fps,'coordinate_space':'scene world; includes armature object transform','units_note':'Set meters_per_unit and up_axis in the reviewed rig config; no automatic unit conversion applied.','bone_order':'parent before children, children sorted by name'},indent=2))
    print('MOTION_EXPORT_COMPLETE',len(worlds),len(names),flush=True)
if __name__=='__main__':main()
