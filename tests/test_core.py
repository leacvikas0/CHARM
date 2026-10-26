import unittest
import numpy as np
from motionkit.core import Motion, validate, locals_from_world, world_from_locals, make_maps, gesture_map, simplify_motion, mix_pose
from motionkit.cli import fingerprint

def sample():
    # Deliberately different names, length, fps and non-topological joint order.
    n=73;parents=np.array([2,2,-1,0,1]);rest=np.repeat(np.eye(4)[None],5,axis=0)
    rest[:,0,3]=[.2,-.2,0,.4,-.4];rest[:,2,3]=[1.,1.,.7,1.,1.]
    world=np.repeat(rest[None],n,axis=0);t=np.linspace(0,4*np.pi,n)
    world[:,3,2,3]+=.15*np.sin(t);world[:,4,2,3]-=.15*np.sin(t)
    return Motion(world,np.array(['L_elbow','R_elbow','Root','L_palm','R_palm']),parents,rest,24.)

def config():
    return {'fps':24.,'meters_per_unit':1.,'up_axis':'z','roles':{'left_hand':'L_palm','right_hand':'R_palm'},'motion_joints':['Root','L_elbow','R_elbow','L_palm','R_palm'],'editable_joints':['L_elbow'],'protected_joints':['Root','R_elbow','L_palm','R_palm'],'anchors_frames':[0,24,48,72]}

class CoreTests(unittest.TestCase):
    def test_fingerprint_normalizes_numeric_storage(self):
        a=sample();a.rest=a.rest.astype(np.float32);b=sample();b.rest=a.rest.astype(np.float64)
        self.assertEqual(fingerprint(a),fingerprint(b))
    def test_arbitrary_hierarchy_roundtrip(self):
        m=sample();validate(m);np.testing.assert_allclose(world_from_locals(locals_from_world(m.world,m.parents),m.parents),m.world,atol=1e-12)
    def test_maps_new_rig(self):
        m=sample();maps,anchors,_=make_maps(m,config())
        for name,mapping in maps.items():
            self.assertEqual(len(mapping),73);self.assertTrue(np.all(np.diff(mapping)>=0));self.assertEqual(mapping[0],0);self.assertEqual(mapping[-1],72)
            if name!='twos':np.testing.assert_array_equal(mapping[anchors],anchors)
        np.testing.assert_array_equal(maps['original'],np.arange(73))
    def test_centimeter_and_meter_rigs_produce_same_time_maps(self):
        a=sample();b=sample();b.world[...,:3,3]*=100;b.rest[...,:3,3]*=100
        ca=config();ca['anchors_frames']=None;cb=config();cb['anchors_frames']=None;cb['meters_per_unit']=.01
        ma,aa,_=make_maps(a,ca);mb,ab,_=make_maps(b,cb)
        np.testing.assert_array_equal(aa,ab)
        for name in ma:np.testing.assert_array_equal(ma[name],mb[name])
    def test_bad_motion_rejected(self):
        m=sample();m.parents[2]=0
        with self.assertRaises(ValueError):validate(m)
        m=sample();m.world[0,0,0,0]=np.nan
        with self.assertRaises(ValueError):validate(m)
    def test_protected_pose_edits(self):
        m=sample();target=sample();a=.15;rot=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]])
        local=locals_from_world(target.world,target.parents);local[:,0,:3,:3]=rot;target.world=world_from_locals(local,target.parents)
        result,report=mix_pose(m,target,config(),.5,5.)
        before=locals_from_world(m.world,m.parents);after=locals_from_world(result,m.parents)
        np.testing.assert_allclose(after[:,[1,2,3,4]],before[:,[1,2,3,4]],atol=1e-12)
        self.assertLessEqual(report['max_applied_angle_degrees'],5.000001)
        np.testing.assert_array_equal(mix_pose(m,target,config(),0,5)[0],m.world)
        target.names[0]='Wrong'
        with self.assertRaises(ValueError):mix_pose(m,target,config(),.5,5.)
    def test_gesture_locality_identity_and_missing_evidence(self):
        baseline=np.arange(73);anchors=np.array([0,24,48,72]);event={'peak':24,'end':48,'delay':2.,'rise':2.}
        np.testing.assert_array_equal(gesture_map(baseline,anchors,[],1,24),baseline)
        np.testing.assert_array_equal(gesture_map(baseline,anchors,[event],0,24),baseline)
        result=gesture_map(baseline,anchors,[event],1,24)
        np.testing.assert_array_equal(result[:25],baseline[:25]);np.testing.assert_array_equal(result[48:],baseline[48:]);np.testing.assert_array_equal(result[anchors],anchors)
        self.assertTrue(np.all(np.diff(result[24:29])>0));self.assertTrue(np.any(result[29:48]<baseline[29:48]))
        with self.assertRaises(ValueError):gesture_map(baseline,anchors,[dict(event,end=47)],1,24)
    def test_curve_preserves_unselected_local_transforms(self):
        m=sample();result,report=simplify_motion(m,config())
        np.testing.assert_allclose(locals_from_world(result,m.parents)[:,[1,2,3,4]],locals_from_world(m.world,m.parents)[:,[1,2,3,4]],atol=1e-12)

if __name__=='__main__':unittest.main()
