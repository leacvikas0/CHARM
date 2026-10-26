"""Run the public synthetic example and verify source-pose/anchor preservation."""
from pathlib import Path
import argparse,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from motionkit.cli import main as cli
from motionkit.core import load_motion

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='runs/synthetic_demo');args=p.parse_args();example=ROOT/'examples/synthetic';output=Path(args.output).resolve()
    code=cli(['run','--input',str(example/'input.npz'),'--config',str(example/'rig.json'),'--events',str(example/'events.json'),'--output',str(output)])
    if code:raise SystemExit(code)
    source=load_motion(example/'input.npz');report=json.loads((output/'report.json').read_text());anchors=np.array(report['anchors'])
    with np.load(output/'timing_maps.npz') as maps:
        for method in ('original','density','adaptive','gesture_subtle','gesture_stronger'):
            mapping=maps[method];assert np.all(np.diff(mapping)>=0);np.testing.assert_array_equal(mapping[anchors],anchors)
            with np.load(output/f'{method}.npz') as result:np.testing.assert_array_equal(result['world'],source.world[mapping])
    print('SYNTHETIC_DEMO_VERIFIED',len(report['methods']),'variants;',len(source.world),'frames;',source.fps,'fps')
if __name__=='__main__':main()
