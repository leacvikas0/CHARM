import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
from .core import load_motion,save_motion,make_maps,simplify_motion,mix_pose,gesture_map,joint_indices,config_scale

def fingerprint(m):
    digest=hashlib.sha256()
    for a in (np.asarray(m.world,dtype='<f8'),np.asarray(m.parents,dtype='<i8'),np.asarray(m.rest,dtype='<f8'),np.array(m.fps,dtype='<f8')):
        digest.update(str(a.shape).encode());digest.update(np.ascontiguousarray(a).tobytes())
    digest.update(json.dumps(m.names.tolist(),ensure_ascii=True).encode())
    return digest.hexdigest()

def file_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write_new(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:json.dump(data,stream,indent=2)

def load_config(path,m=None):
    config=json.loads(Path(path).read_text(encoding='utf-8-sig'));config_scale(config)
    if config.get('review_required',False):raise ValueError('Review rig roles, units, axes and protected joints; then set review_required=false')
    if m:
        for field in ('motion_joints','editable_joints','protected_joints','world_protected_joints'):joint_indices(m,config.get(field,[]))
        joint_indices(m,[v for v in config.get('roles',{}).values() if v])
    return config

def suggested_config(m):
    short={str(n).split(':')[-1].lower():str(n) for n in m.names}
    roles={key:short.get(name) for key,name in [('left_hand','lefthand'),('right_hand','righthand'),('left_foot','leftfoot'),('right_foot','rightfoot'),('chest','spine2'),('head','head')]}
    editable=[str(n) for n in m.names if str(n).split(':')[-1].lower() in ('spine','spine1','spine2','neck','head','leftshoulder','rightshoulder','leftarm','rightarm','leftforearm','rightforearm')]
    motion=[str(n) for n in m.names if 'hand' not in str(n).lower() or str(n).split(':')[-1].lower() in ('lefthand','righthand')]
    return {'schema_version':1,'review_required':True,'fps':m.fps,'meters_per_unit':1.,'up_axis':'z','roles':roles,'motion_joints':motion,'editable_joints':editable,'protected_joints':[str(n) for n in m.names if str(n) not in editable],'world_protected_joints':[str(m.names[j]) for j,p in enumerate(m.parents) if p<0],'anchors_frames':None,'curve_tolerances_degrees':{n:1.5 if any(x in n.lower() for x in ('spine','head','neck')) else 2.5 for n in editable},'timing':{'density_strength':.85,'density_smoothing_seconds':1.25/30,'anchor_prominence_m':.035,'feature_peak_distance_seconds':.4,'anchor_separation_seconds':14/30,'max_anchor_gap_seconds':1.5,'target_anchor_gap_seconds':40/30,'max_hold_seconds':.1,'hold_anchor_radius_seconds':4/30},'pose_sources':{}}

def run(args):
    config=load_config(args.config);m=load_motion(args.input,args.key,config.get('fps'));load_config(args.config,m)
    poses={'original':m.world};reports={}
    basic=['original','twos','density','adaptive','curves','curves_timing']
    available=list(basic);sources=config.get('pose_sources',{})
    for name in sources:
        if name in basic or not name.replace('_','').isalnum():raise ValueError('Invalid/colliding pose source name')
        available.extend([name,name+'_timing'])
    events=None
    if args.events:
        events=json.loads(Path(args.events).read_text(encoding='utf-8-sig'))
        if events.get('motion_sha256')!=fingerprint(m):raise ValueError('Gesture event fingerprint does not match this motion; verify events on the new clip')
        if events.get('frames')!=len(m.world) or not np.isclose(events.get('fps',0),m.fps):raise ValueError('Gesture event timeline differs')
        if any(not e.get('verified',False) for e in events.get('events',[])):raise ValueError('All applied gesture events must be independently verified')
        available.extend(['gesture_subtle','gesture_stronger'])
    methods=available if args.methods==['all'] else args.methods
    if any(name not in available for name in methods):raise ValueError('Unavailable method; available: '+', '.join(available))
    if any(name in ('density','adaptive','curves_timing') or name.endswith('_timing') or name.startswith('gesture_') for name in methods):
        maps,anchors,features=make_maps(m,config)
    else:
        n=len(m.world);maps={'original':np.arange(n),'twos':(np.arange(n)//2)*2};maps['twos'][-1]=n-1;anchors=np.array([0,n-1]);features={}
    if any(name.startswith('curves') for name in methods):poses['curves'],reports['curves']=simplify_motion(m,config)
    for name,spec in sources.items():
        if name not in methods and name+'_timing' not in methods:continue
        target=load_motion(Path(args.config).resolve().parent/spec['path'],spec.get('key','world'),m.fps)
        poses[name],reports[name]=mix_pose(m,target,config,float(spec.get('strength',1.)),spec.get('angle_cap_degrees'))
    if events:
        for profile,default_strength in [('subtle',.7),('stronger',1.25)]:
            name='gesture_'+profile
            if name not in methods:continue
            selected=[e for e in events.get('events',[]) if profile in e.get('profiles',['subtle','stronger'])]
            maps[name]=gesture_map(maps['density'],anchors,selected,float(events.get('strengths',{}).get(profile,default_strength)),m.fps,int(events.get('max_source_step',3)),int(events.get('max_source_shift',5)))
    output=Path(args.output);output.mkdir(parents=True,exist_ok=False)
    report={'schema_version':1,'motion_sha256':fingerprint(m),'input_file_sha256':file_sha(args.input),'config':config,'frames':len(m.world),'fps':m.fps,'anchors':anchors.tolist(),'pose_audits':reports,'methods':{},'limits':['Timing changes dynamics/velocities, not source articulated poses.','No collision correction, skinning fix or cloth/physics simulation is performed.','New rig calibration and learned-style source generation are explicit upstream steps.']}
    np.savez_compressed(output/'timing_maps.npz',**maps,anchors=anchors,**features)
    for name in methods:
        pose_key='original';map_key=name
        if name=='curves':pose_key='curves';map_key='original'
        elif name=='curves_timing':pose_key='curves';map_key='adaptive'
        elif name in sources:pose_key=name;map_key='original'
        elif name.endswith('_timing') and name[:-7] in sources:pose_key=name[:-7];map_key='adaptive'
        mapping=maps[map_key];world=poses[pose_key][mapping];save_motion(output/f'{name}.npz',world,m,mapping)
        report['methods'][name]={'pose_source':pose_key,'time_map':map_key,'unique_source_frames':int(len(np.unique(mapping))),'held_output_transitions':int(np.sum(np.diff(mapping)==0)),'max_source_step':int(np.diff(mapping).max()),'max_source_phase_shift':int(np.abs(mapping-np.arange(len(mapping))).max()),'npz_sha256':file_sha(output/f'{name}.npz')}
    (output/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'output':str(output.resolve()),'methods':list(report['methods']),'frames':len(m.world),'fps':m.fps}))

def parser():
    p=argparse.ArgumentParser(description='Portable post-retarget motion techniques. Run from the toolkit directory.');sub=p.add_subparsers(dest='command',required=True)
    for name in ('template','validate','events-template'):
        q=sub.add_parser(name);q.add_argument('--input',required=True);q.add_argument('--key',default='world');q.add_argument('--fps',type=float)
        if name!='validate':q.add_argument('--output',required=True)
        if name=='validate':q.add_argument('--config')
    q=sub.add_parser('run');q.add_argument('--input',required=True);q.add_argument('--key',default='world');q.add_argument('--config',required=True);q.add_argument('--output',required=True);q.add_argument('--events');q.add_argument('--methods',nargs='+',default=['all'])
    q=sub.add_parser('mix');q.add_argument('--input',required=True);q.add_argument('--key',default='world');q.add_argument('--style',required=True);q.add_argument('--style-key',default='world');q.add_argument('--config',required=True);q.add_argument('--output',required=True);q.add_argument('--strength',type=float,default=.35);q.add_argument('--cap',type=float,default=5.);q.add_argument('--uncapped',action='store_true')
    return p

def main(argv=None):
    args=parser().parse_args(argv)
    try:
        if args.command=='run':run(args)
        elif args.command=='mix':
            c=load_config(args.config);m=load_motion(args.input,args.key,c.get('fps'));load_config(args.config,m);target=load_motion(args.style,args.style_key,m.fps)
            path=Path(args.output)
            if path.exists():raise FileExistsError(path)
            world,report=mix_pose(m,target,c,args.strength,None if args.uncapped else args.cap);path.parent.mkdir(parents=True,exist_ok=True);save_motion(path,world,m);print(json.dumps(report))
        else:
            c=load_config(args.config) if args.command=='validate' and args.config else None
            m=load_motion(args.input,args.key,c.get('fps') if c else args.fps)
            if args.command=='template':write_new(args.output,suggested_config(m));print('Rig template written; review it before use.')
            elif args.command=='events-template':write_new(args.output,{'schema_version':1,'motion_sha256':fingerprint(m),'frames':len(m.world),'fps':m.fps,'strengths':{'subtle':.7,'stronger':1.25},'max_source_step':3,'max_source_shift':5,'events':[]});print('Empty clip-bound event template written.')
            else:
                if c:load_config(args.config,m)
                print(json.dumps({'frames':len(m.world),'joints':len(m.names),'fps':m.fps,'motion_sha256':fingerprint(m)}))
    except (ValueError,OSError,KeyError) as exc:
        print(f'motionkit: {exc}',file=sys.stderr);return 2
    return 0
