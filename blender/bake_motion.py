"""Apply target-rig world transforms; save a verified separate animation and optionally render."""
from pathlib import Path
import argparse,json,sys,subprocess
import bpy,numpy as np
from mathutils import Matrix,Vector

def main():
    p=argparse.ArgumentParser();p.add_argument('--motion',required=True);p.add_argument('--armature',required=True);p.add_argument('--output',required=True);p.add_argument('--render',action='store_true');p.add_argument('--camera');p.add_argument('--camera-config');p.add_argument('--view',default='front');p.add_argument('--width',type=int,default=460);p.add_argument('--height',type=int,default=720);p.add_argument('--tolerance',type=float,default=1e-4)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);output=Path(args.output).resolve()
    if output.exists():raise FileExistsError(output)
    with np.load(args.motion,allow_pickle=False) as data:
        world=data['world'];names=data['names'].tolist();parents=data['parents'];rest=data['rest'];fps=float(data['fps'])
    arm=bpy.data.objects.get(args.armature);scene=bpy.context.scene
    if arm is None or arm.type!='ARMATURE':raise ValueError('Named armature does not exist')
    if set(names)!=set(b.name for b in arm.data.bones):raise ValueError('Input bones do not match target scene armature')
    if world.shape!=(len(world),len(names),4,4) or len(world)<2 or not np.isfinite(world).all():raise ValueError('Invalid world arrays')
    if not np.isfinite(fps) or fps<=0 or args.tolerance<=0:raise ValueError('Invalid fps/tolerance')
    for j,name in enumerate(names):
        actual_parent=arm.data.bones[name].parent;expected=None if parents[j]<0 else names[parents[j]]
        if (actual_parent.name if actual_parent else None)!=expected:raise ValueError('Input hierarchy differs from target rig')
    bind=np.array([arm.matrix_world@arm.data.bones[name].matrix_local for name in names])
    if not np.allclose(bind,rest,atol=args.tolerance,rtol=0):raise ValueError('Rest calibration/object transform differs; retarget to this scene first')
    if args.render and scene.camera is None and not args.camera:raise ValueError('Choose a render camera')
    output.mkdir(parents=True,exist_ok=False);arm.animation_data_clear()
    scene.frame_start=1;scene.frame_end=len(world);scene.render.fps=round(fps);scene.render.fps_base=round(fps)/fps
    inverse_bind={name:arm.data.bones[name].matrix_local.inverted() for name in names};previous={};max_error=0.
    for f,frame_world in enumerate(world):
        scene.frame_set(f+1)
        # PoseBone.matrix_basis uses actual target bind orientation, not global axes.
        for j,name in enumerate(names):
            bone=arm.pose.bones[name];bone.rotation_mode='QUATERNION';target=arm.matrix_world.inverted()@Matrix(frame_world[j].tolist())
            if parents[j]>=0:
                parent_name=names[parents[j]];parent_target=arm.matrix_world.inverted()@Matrix(frame_world[parents[j]].tolist())
                local=parent_target.inverted()@target;local_bind=arm.data.bones[parent_name].matrix_local.inverted()@arm.data.bones[name].matrix_local
                basis=local_bind.inverted()@local
            else:basis=inverse_bind[name]@target
            bone.matrix_basis=basis;q=bone.rotation_quaternion.copy()
            if name in previous and q.dot(previous[name])<0:q.negate()
            bone.rotation_quaternion=q;previous[name]=q.copy()
            for field in ('location','rotation_quaternion','scale'):bone.keyframe_insert(data_path=field,frame=f+1)
        bpy.context.view_layer.update();actual=np.array([arm.matrix_world@arm.pose.bones[name].matrix for name in names]);max_error=max(max_error,float(np.abs(actual-frame_world).max()))
    if max_error>args.tolerance:raise ValueError(f'Replay failed: max matrix error {max_error}; inspect constraints/inherit-scale/rig calibration')
    action=arm.animation_data.action
    for layer in action.layers:
        for strip in layer.strips:
            if hasattr(strip,'channelbags'):
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        for point in curve.keyframe_points:point.interpolation='CONSTANT'
    if args.camera:scene.camera=bpy.data.objects[args.camera]
    if args.camera_config:
        if scene.camera is None:raise ValueError('Camera config requires a camera')
        config=json.loads(Path(args.camera_config).read_text());spec=config.get(args.view+'_camera',config.get(args.view))
        if spec is None:raise ValueError('Requested camera view is absent')
        camera=scene.camera;camera.animation_data_clear();camera.data.animation_data_clear()
        for constraint in list(camera.constraints):camera.constraints.remove(constraint)
        camera.location=Vector(spec['location']);camera.rotation_euler=(Vector(spec['center'])-camera.location).to_track_quat('-Z','Y' if args.view=='front' else 'Z').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=spec['ortho_scale']
    scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(output/'animation.blend'))
    bpy.ops.wm.open_mainfile(filepath=str(output/'animation.blend'));scene=bpy.context.scene;arm=bpy.data.objects[args.armature];saved_error=0.
    for f,expected in enumerate(world):
        scene.frame_set(f+1);bpy.context.view_layer.update();actual=np.array([arm.matrix_world@arm.pose.bones[name].matrix for name in names]);saved_error=max(saved_error,float(np.abs(actual-expected).max()))
    if saved_error>args.tolerance:raise ValueError(f'Saved animation replay failed: {saved_error}')
    report={'frames':len(world),'fps':fps,'replay_max_error':max_error,'saved_replay_max_error':saved_error,'matrix_tolerance_scene_units':args.tolerance,'constant_integer_frame_keys':True,'rendered':args.render}
    if args.render:
        scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=args.width;scene.render.resolution_y=args.height;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
        frames=output/'frames';frames.mkdir()
        for f in range(len(world)):
            scene.frame_set(f+1);scene.render.filepath=str(frames/f'f_{f:04d}.png');bpy.ops.render.render(write_still=True);print('MOTION_RENDER_FRAME',f+1,flush=True)
        subprocess.run(['ffmpeg','-y','-framerate',str(fps),'-i',str(frames/'f_%04d.png'),'-frames:v',str(len(world)),'-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(output/'video.mp4')],check=True,stdout=subprocess.DEVNULL)
    (output/'verification.json').write_text(json.dumps(report,indent=2));print('MOTION_BAKE_VERIFIED',json.dumps(report),flush=True)
if __name__=='__main__':main()
