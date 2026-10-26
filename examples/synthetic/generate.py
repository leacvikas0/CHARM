"""Original procedural example; no captured motion or third-party character assets."""
from pathlib import Path
import argparse,json,sys
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from motionkit.core import Motion,world_from_locals,save_motion
from motionkit.cli import fingerprint,suggested_config

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='runs/synthetic_input');args=p.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    if (out/'input.npz').exists():raise FileExistsError(out/'input.npz')
    names=np.array(['root','spine','chest','head','shoulder.L','elbow.L','palm.L','shoulder.R','elbow.R','palm.R','hip.L','foot.L','hip.R','foot.R'])
    parents=np.array([-1,0,1,2,2,4,5,2,7,8,0,10,0,12]);offsets=np.array([[0,0,.9],[0,0,.15],[0,0,.18],[0,0,.28],[.15,0,.1],[.26,0,0],[.25,0,0],[-.15,0,.1],[-.26,0,0],[-.25,0,0],[.11,0,-.1],[0,0,-.8],[-.11,0,-.1],[0,0,-.8]])
    local=np.repeat(np.eye(4)[None],len(names),axis=0);local[:,:3,3]=offsets;rest=world_from_locals(local[None],parents)[0]
    frames=180;animated=np.repeat(local[None],frames,axis=0);keys=np.array([0,30,45,65,90,115,135,155,179]);values=np.array([.1,-.65,.9,.05,-.45,-.2,.75,-.35,.1])
    t=np.arange(frames);angle=np.zeros(frames)
    for a,b,left,right in zip(keys[:-1],keys[1:],values[:-1],values[1:]):
        u=np.arange(b-a+1)/(b-a);angle[a:b+1]=left+(right-left)*(u*u*(3-2*u))
    for j,sign in [(4,-1),(7,1)]:animated[:,j,:3,:3]=Rotation.from_rotvec(np.c_[np.zeros(frames),sign*angle,np.zeros(frames)]).as_matrix()
    for j,sign in [(5,-1),(8,1)]:animated[:,j,:3,:3]=Rotation.from_rotvec(np.c_[np.zeros(frames),sign*(.3+.4*np.sin(t/19)),np.zeros(frames)]).as_matrix()
    animated[:,3,:3,:3]=Rotation.from_rotvec(np.c_[np.zeros(frames),np.zeros(frames),.12*np.sin(t/31)]).as_matrix()
    animated[:,0,2,3]+=.025*np.sin(t/9)
    m=Motion(world_from_locals(animated,parents),names,parents,rest,30.);save_motion(out/'input.npz',m.world,m)
    rig=suggested_config(m);rig.update(review_required=False,roles={'left_hand':'palm.L','right_hand':'palm.R','head':'head','chest':'chest','left_foot':'foot.L','right_foot':'foot.R'},motion_joints=names.tolist(),editable_joints=['spine','chest','head','shoulder.L','elbow.L','shoulder.R','elbow.R'],protected_joints=['root','palm.L','palm.R','hip.L','foot.L','hip.R','foot.R'],world_protected_joints=['root','foot.L','foot.R'],anchors_frames=[0,45,90,135,179])
    rig['curve_tolerances_degrees']={name:1.5 for name in rig['editable_joints']};(out/'rig.json').write_text(json.dumps(rig,indent=2))
    events={'schema_version':1,'motion_sha256':fingerprint(m),'frames':frames,'fps':30.,'strengths':{'subtle':.7,'stronger':1.25},'max_source_step':3,'max_source_shift':5,'events':[{'id':'designed_arm_accent','peak':45,'end':90,'delay':2.5,'rise':2.,'verified':True,'profiles':['subtle','stronger'],'no_freeze_seconds':5/30,'evidence':'Procedurally authored arm-angle key at frame 45; synthetic example, no physical-contact claim.'}]}
    (out/'events.json').write_text(json.dumps(events,indent=2));print('SYNTHETIC_INPUT_CREATED',out)
if __name__=='__main__':main()
