from dataclasses import dataclass
from pathlib import Path
import math
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
from scipy.spatial.transform import Rotation,Slerp

@dataclass
class Motion:
    world: np.ndarray
    names: np.ndarray
    parents: np.ndarray
    rest: np.ndarray
    fps: float

def hierarchy_order(parents):
    parents=np.asarray(parents);order=[];done=set();visiting=set()
    def visit(j):
        if j in done:return
        if j in visiting:raise ValueError('Skeleton hierarchy contains a cycle')
        visiting.add(j);p=int(parents[j])
        if p>=0:visit(p)
        visiting.remove(j);done.add(j);order.append(j)
    for j in range(len(parents)):visit(j)
    return order

def validate(m):
    if m.world.ndim!=4 or m.world.shape[2:]!=(4,4) or len(m.world)<2:raise ValueError('world must have shape [F>=2,J,4,4]')
    n,j=m.world.shape[:2]
    if m.names.shape!=(j,) or m.names.dtype.kind not in 'US' or len(set(m.names.tolist()))!=j:raise ValueError('Unique string bone names are required')
    if m.parents.shape!=(j,) or not np.issubdtype(m.parents.dtype,np.integer) or np.any(m.parents < -1) or np.any(m.parents>=j):raise ValueError('Invalid parent indices')
    if m.rest.shape!=(j,4,4):raise ValueError('rest must have shape [J,4,4]')
    hierarchy_order(m.parents)
    if not math.isfinite(m.fps) or m.fps<=0:raise ValueError('fps must be finite and positive')
    for label,a in [('world',m.world),('rest',m.rest)]:
        if not np.isfinite(a).all():raise ValueError(f'{label} contains nonfinite values')
        if not np.allclose(a[...,3,:],np.array([0,0,0,1]),atol=1e-6,rtol=0):raise ValueError(f'{label} has invalid homogeneous rows')
        if np.any(np.abs(np.linalg.det(a[...,:3,:3]))<1e-10):raise ValueError(f'{label} contains singular transforms')
    return m

def load_motion(path,key='world',fps=None):
    with np.load(path,allow_pickle=False) as data:
        if key not in data:raise ValueError(f'Array {key!r} is absent in {path}')
        stored_fps=float(data['fps']) if 'fps' in data else None
        if fps is not None and stored_fps is not None and not np.isclose(fps,stored_fps):raise ValueError('Configured fps differs from stored fps; resample explicitly first')
        rate=stored_fps if stored_fps is not None else fps
        if rate is None:raise ValueError('NPZ has no fps; supply it explicitly in the rig config')
        return validate(Motion(np.array(data[key],dtype=float),np.array(data['names']).astype(str),np.array(data['parents']),np.array(data['rest'],dtype=float),float(rate)))

def save_motion(path,world,m,indices=None):
    data=dict(world=world,names=m.names,parents=m.parents,rest=m.rest,fps=np.array(m.fps))
    if indices is not None:data['indices']=indices
    np.savez_compressed(path,**data)

def locals_from_world(world,parents):
    result=world.copy()
    for j,p in enumerate(parents):
        if p>=0:result[:,j]=np.linalg.inv(world[:,p])@world[:,j]
    return result

def world_from_locals(local,parents):
    result=local.copy()
    for j in hierarchy_order(parents):
        p=int(parents[j])
        if p>=0:result[:,j]=result[:,p]@local[:,j]
    return result

def positions(world,joints):return world[...,:3,3][:,joints]

def joint_indices(m,names):
    lookup={str(n):i for i,n in enumerate(m.names)}
    try:return [lookup[n] for n in names]
    except KeyError as exc:raise ValueError(f'Configured bone {exc.args[0]!r} is absent; edit the rig config') from exc

def config_scale(config):
    scale=config.get('meters_per_unit')
    if not isinstance(scale,(int,float)) or not math.isfinite(scale) or scale<=0:raise ValueError('Set a positive meters_per_unit')
    if config.get('up_axis') not in ('x','y','z'):raise ValueError('Set up_axis to x, y or z')
    return float(scale)

def event_anchors(m,config):
    scale=config_scale(config);n=len(m.world);settings=config.get('timing',{})
    provided=config.get('anchors_frames')
    if provided is not None:
        raw=np.asarray(provided)
        if raw.ndim!=1 or not np.issubdtype(raw.dtype,np.integer) or np.any(raw<0) or np.any(raw>=n):raise ValueError('anchors_frames must contain in-range integers')
        return np.unique(np.r_[0,raw,n-1]).astype(int)
    roles=config.get('roles',{})
    if not all(roles.get(k) for k in ('left_hand','right_hand')):raise ValueError('Automatic anchors require left_hand/right_hand roles; or specify anchors_frames')
    hands=positions(m.world,joint_indices(m,[roles['left_hand'],roles['right_hand']]))*scale
    span=np.linalg.norm(hands[:,0]-hands[:,1],axis=-1);height=hands[:,:,('x','y','z').index(config['up_axis'])].mean(-1)
    distance=max(1,round(settings.get('feature_peak_distance_seconds',.4)*m.fps))
    separation=max(1,round(settings.get('anchor_separation_seconds',14/30)*m.fps))
    prominence=float(settings.get('anchor_prominence_m',.035));scores={0:1e6,n-1:1e6}
    if prominence<=0:raise ValueError('anchor_prominence_m must be positive')
    for signal in (span,-span,height,-height):
        peaks,properties=find_peaks(signal,distance=distance,prominence=prominence)
        for f,score in zip(peaks,properties['prominences']):scores[int(f)]=max(scores.get(int(f),0),float(score))
    chosen=[0,n-1]
    for f in sorted(scores,key=lambda f:scores[f],reverse=True):
        if min(abs(f-x) for x in chosen)>=separation:chosen.append(f)
    anchors=sorted(set(chosen));extra=[]
    max_gap=max(2,round(settings.get('max_anchor_gap_seconds',1.5)*m.fps));target_gap=max(1,round(settings.get('target_anchor_gap_seconds',40/30)*m.fps))
    for a,b in zip(anchors[:-1],anchors[1:]):
        if b-a>max_gap:extra.extend(np.linspace(a,b,int(np.ceil((b-a)/target_gap))+1)[1:-1].round().astype(int))
    return np.unique(np.r_[anchors,extra]).astype(int)

def density_map(speed,anchors,strength=.85,sigma=1.25):
    speed=np.asarray(speed,dtype=float);n=len(speed)+1
    if speed.ndim!=1 or not np.isfinite(speed).all() or np.any(speed<0):raise ValueError('Invalid displacement sequence')
    if not np.isfinite(strength) or strength<0 or not np.isfinite(sigma) or sigma<=0:raise ValueError('Invalid density settings')
    if speed.max(initial=0)<1e-12:return np.arange(n,dtype=float)
    smooth=gaussian_filter1d(speed,sigma,mode='nearest');density=smooth/max(smooth.mean(),1e-12)
    dwell=np.clip(np.maximum(density,.08)**(-strength),.35,3.)
    result=np.arange(n,dtype=float)
    for a,b in zip(anchors[:-1],anchors[1:]):
        if b-a<=1:continue
        cumulative=np.r_[0,np.cumsum(dwell[a:b])];output=a+cumulative/cumulative[-1]*(b-a)
        result[a:b+1]=np.interp(np.arange(a,b+1),output,np.arange(a,b+1))
    result[anchors]=anchors
    return result

def make_maps(m,config):
    validate(m);scale=config_scale(config);settings=config.get('timing',{});n=len(m.world)
    selected=joint_indices(m,config.get('motion_joints',m.names.tolist()))
    if not selected:raise ValueError('motion_joints cannot be empty')
    xyz=positions(m.world,selected)*scale;speed=np.linalg.norm(np.diff(xyz,axis=0),axis=-1).sum(-1)
    anchors=event_anchors(m,config)
    raw=density_map(speed,anchors,float(settings.get('density_strength',.85)),float(settings.get('density_smoothing_seconds',1.25/30))*m.fps)
    maps={'original':np.arange(n),'twos':(np.arange(n)//2)*2,'density':np.rint(raw).astype(int)};maps['twos'][-1]=n-1
    max_hold=max(1,round(settings.get('max_hold_seconds',.1)*m.fps));near_radius=max(1,round(settings.get('hold_anchor_radius_seconds',4/30)*m.fps))
    progress=np.gradient(raw);result=np.empty(n,dtype=int);i=0
    while i<n:
        near=min(abs(i-int(a)) for a in anchors);hold=max_hold if near<near_radius else (min(2,max_hold) if progress[i]<1.15 else 1)
        future=anchors[anchors>i];next_anchor=int(future[0]) if len(future) else n
        end=min(i+hold,next_anchor,n);result[i:end]=int(np.clip(np.rint(raw[i]),0,n-1));i=end
    result[anchors]=anchors;result=np.maximum.accumulate(result);result[-1]=n-1;maps['adaptive']=result
    return maps,anchors,{'density_float_map':raw,'body_displacement':speed}

def simplify_rotations(matrices,tolerance):
    if not np.isfinite(tolerance) or tolerance<=0:raise ValueError('Rotation tolerance must be positive')
    u,_,vt=np.linalg.svd(matrices);rot=u@vt
    if np.linalg.det(rot).min()<.99:raise ValueError('Pose editing requires proper rotations; fix reflected local bases first')
    scale=np.swapaxes(rot,-1,-2)@matrices;rotations=Rotation.from_matrix(rot);keys={0,len(rot)-1};stack=[(0,len(rot)-1)]
    while stack:
        a,b=stack.pop()
        if b-a<2:continue
        indices=np.arange(a,b+1);interp=Slerp([a,b],rotations[[a,b]])(indices);error=(interp.inv()*rotations[indices]).magnitude();worst=int(np.argmax(error))+a
        if error.max()>tolerance:keys.add(worst);stack.extend([(a,worst),(worst,b)])
    keys=sorted(keys)
    return Slerp(keys,rotations[keys])(np.arange(len(rot))).as_matrix()@scale,keys

def editable_indices(m,config):
    selected=joint_indices(m,config.get('editable_joints',[]));protected=joint_indices(m,config.get('protected_joints',[]))
    if set(selected)&set(protected):raise ValueError('editable_joints overlaps protected_joints')
    if any(m.parents[j]<0 for j in selected):raise ValueError('Root pose edits are outside this toolkit scope')
    return selected

def pose_audit(original,result,selected,config):
    before=locals_from_world(original.world,original.parents);after=locals_from_world(result,original.parents)
    protected=[j for j in range(len(original.names)) if j not in selected]
    error=float(np.abs(after[:,protected]-before[:,protected]).max()) if protected else 0.
    world_protected=joint_indices(original,config.get('world_protected_joints',[]))
    world_error=float(np.abs(result[:,world_protected]-original.world[:,world_protected]).max()) if world_protected else 0.
    if error>1e-9 or world_error>1e-9:raise ValueError('Pose modification moved a protected transform; check editable bones and hierarchy')
    return {'protected_local_max_error':error,'protected_world_max_error':world_error,'geometry_audit_run':False}

def simplify_motion(m,config):
    local=locals_from_world(m.world,m.parents);selected=editable_indices(m,config);counts={}
    for j in selected:
        tolerance=float(config.get('curve_tolerances_degrees',{}).get(str(m.names[j]),2.5))
        local[:,j,:3,:3],keys=simplify_rotations(local[:,j,:3,:3],np.deg2rad(tolerance));counts[str(m.names[j])]=len(keys)
    result=world_from_locals(local,m.parents) if selected else m.world.copy()
    return result,dict(pose_audit(m,result,selected,config),key_counts=counts)

def mix_pose(m,target,config,strength=1.,angle_cap_degrees=5.):
    validate(m);validate(target)
    if not np.array_equal(m.names,target.names) or not np.array_equal(m.parents,target.parents) or not np.allclose(m.rest,target.rest,atol=1e-8,rtol=0) or m.world.shape!=target.world.shape or not np.isclose(m.fps,target.fps):raise ValueError('Pose source must be frame/fps/name/hierarchy/rest-aligned to this target rig')
    if not math.isfinite(strength) or not 0<=strength<=1:raise ValueError('Pose strength must be in [0,1]')
    if angle_cap_degrees is not None and (not math.isfinite(angle_cap_degrees) or angle_cap_degrees<=0):raise ValueError('Angle cap must be positive or None')
    selected=editable_indices(m,config)
    if strength==0 or not selected:return m.world.copy(),dict(pose_audit(m,m.world,[],config),max_applied_angle_degrees=0.)
    local=locals_from_world(m.world,m.parents);other=locals_from_world(target.world,target.parents);max_angle=0.
    for j in selected:
        delta=np.linalg.inv(local[:,j,:3,:3])@other[:,j,:3,:3]
        if not np.allclose(np.swapaxes(delta,-1,-2)@delta,np.eye(3),atol=1e-6) or np.any(np.linalg.det(delta)<.99):raise ValueError('Pose mixing requires rotational deltas; source has different scale/shear')
        vectors=Rotation.from_matrix(delta).as_rotvec()*strength;magnitude=np.linalg.norm(vectors,axis=-1)
        if angle_cap_degrees is not None:vectors*=np.minimum(1,np.deg2rad(angle_cap_degrees)/np.maximum(magnitude,1e-12))[:,None]
        max_angle=max(max_angle,float(np.rad2deg(np.linalg.norm(vectors,axis=-1)).max()));local[:,j,:3,:3]=local[:,j,:3,:3]@Rotation.from_rotvec(vectors).as_matrix()
    result=world_from_locals(local,m.parents)
    return result,dict(pose_audit(m,result,selected,config),max_applied_angle_degrees=max_angle)

def gesture_map(baseline,anchors,events,strength,fps,max_step=3,max_shift=5):
    base=np.asarray(baseline)
    if base.ndim!=1 or not np.issubdtype(base.dtype,np.integer) or np.any(np.diff(base)<0):raise ValueError('Expected monotone integer baseline map')
    if not np.isfinite(strength) or not 0<=strength<=1.5 or not np.isfinite(fps) or fps<=0:raise ValueError('Invalid gesture strength/fps')
    result=base.copy();occupied=set()
    if strength==0:return result
    for event in events:
        a,b=event['peak'],event['end'];delay=event['delay'];rise=event['rise']
        if not isinstance(a,int) or not isinstance(b,int) or not 0<=a<b<len(base) or a not in anchors or b not in anchors or any(a<x<b for x in anchors):raise ValueError('Gesture window must span adjacent verified anchors')
        if set(range(a+1,b))&occupied:raise ValueError('Gesture windows overlap')
        occupied.update(range(a+1,b))
        if not np.isfinite(delay) or delay<0 or not np.isfinite(rise) or rise<=0:raise ValueError('Invalid gesture delay/rise')
        t=np.arange(b-a+1,dtype=float);u=t/(b-a);shape=(1-np.exp(-t/rise))*(1-u)**2;shape/=max(shape.max(),1e-12)
        target=base[a:b+1]-delay*strength*shape;target[[0,-1]]=base[[a,b]]
        values=np.arange(int(base[a]),int(base[b])+1);count=len(values)
        cost=np.full((len(t),count),np.inf);prev=np.full((len(t),count),-1,dtype=int);cost[0,0]=0.
        no_freeze=max(1,round(event.get('no_freeze_seconds',5/30)*fps))
        for i in range(1,len(t)):
            f=a+i
            for j,value in enumerate(values):
                if abs(value-int(base[f]))>max_shift or (i==len(t)-1 and value!=base[b]):continue
                for step in range(1 if i<=no_freeze else 0,max_step+1):
                    k=j-step
                    if k<0 or not np.isfinite(cost[i-1,k]):continue
                    c=cost[i-1,k]+(value-target[i])**2+.08*(value-base[f])**2+.12*(step-int(base[f]-base[f-1]))**2
                    if c<cost[i,j]:cost[i,j]=c;prev[i,j]=k
        j=count-1
        if not np.isfinite(cost[-1,j]):raise ValueError('No feasible gesture edit; reduce its timing budget')
        sequence=np.empty(len(t),dtype=int)
        for i in range(len(t)-1,-1,-1):
            sequence[i]=values[j]
            if i:j=prev[i,j]
        result[a:b+1]=sequence
    return result
