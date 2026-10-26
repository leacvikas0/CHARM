import json,subprocess,sys,tempfile,unittest
from pathlib import Path
import numpy as np
from test_core import sample,config
from motionkit.core import save_motion
ROOT=Path(__file__).resolve().parents[1]
class CLITests(unittest.TestCase):
    def call(self,*args):return subprocess.run([sys.executable,'-m','motionkit',*map(str,args)],cwd=ROOT,capture_output=True,text=True)
    def test_nonelf_run_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);save_motion(root/'motion.npz',sample().world,sample());(root/'rig.json').write_text(json.dumps(config()))
            r=self.call('run','--input',root/'motion.npz','--config',root/'rig.json','--output',root/'results');self.assertEqual(r.returncode,0,r.stderr)
            with np.load(root/'results/density.npz') as d:self.assertEqual(d['world'].shape,(73,5,4,4));self.assertEqual(float(d['fps']),24)
            r=self.call('run','--input',root/'motion.npz','--config',root/'rig.json','--output',root/'results');self.assertNotEqual(r.returncode,0)
    def test_identity_and_twos_need_no_hand_roles(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);save_motion(root/'motion.npz',sample().world,sample());c=config();c['roles']={};c['anchors_frames']=None;(root/'rig.json').write_text(json.dumps(c))
            r=self.call('run','--input',root/'motion.npz','--config',root/'rig.json','--methods','original','twos','--output',root/'results');self.assertEqual(r.returncode,0,r.stderr)
    def test_unreviewed_config_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);save_motion(root/'motion.npz',sample().world,sample())
            r=self.call('template','--input',root/'motion.npz','--output',root/'rig.json');self.assertEqual(r.returncode,0,r.stderr)
            r=self.call('run','--input',root/'motion.npz','--config',root/'rig.json','--output',root/'results');self.assertNotEqual(r.returncode,0);self.assertIn('review',r.stderr.lower())
    def test_wrong_motion_events_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);save_motion(root/'motion.npz',sample().world,sample());(root/'rig.json').write_text(json.dumps(config()));(root/'events.json').write_text(json.dumps({'motion_sha256':'wrong','events':[]}))
            r=self.call('run','--input',root/'motion.npz','--config',root/'rig.json','--events',root/'events.json','--output',root/'results');self.assertNotEqual(r.returncode,0);self.assertIn('fingerprint',r.stderr.lower())

if __name__=='__main__':unittest.main()
