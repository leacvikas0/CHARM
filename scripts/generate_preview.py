"""Render an original synthetic skeleton preview; optional Pillow dependency."""
from pathlib import Path
import argparse
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',default='runs/synthetic_demo');p.add_argument('--output',default='runs/synthetic-timing-demo.gif');args=p.parse_args();run=Path(args.run)
    methods=[('original','Original timing'),('density','Density'),('gesture_subtle','Gesture-aware')];datasets=[]
    for key,label in methods:
        with np.load(run/f'{key}.npz') as d:datasets.append((d['world'][...,:3,3].copy(),d['parents'].copy(),label))
    images=[];font=ImageFont.load_default(size=17);small=ImageFont.load_default(size=12)
    for f in range(0,180,2):
        image=Image.new('RGB',(900,420),'#101b20');draw=ImageDraw.Draw(image)
        for panel,(positions,parents,label) in enumerate(datasets):
            offset=panel*300;draw.text((offset+18,18),label,fill='#dce9ec',font=font);draw.line((offset+8,378,offset+292,378),fill='#35505a',width=1)
            points=[(offset+150+float(x)*165,378-float(z)*180) for x,y,z in positions[f]]
            for j,parent in enumerate(parents):
                if parent<0:continue
                color='#65d8bd' if j in (4,5,6) else '#f3b276' if j in (7,8,9) else '#aec7d0'
                draw.line((*points[parent],*points[j]),fill=color,width=5)
            for j,(x,y) in enumerate(points):draw.ellipse((x-4,y-4,x+4,y+4),fill='#e2f0f3')
            x,y=points[3];draw.ellipse((x-15,y-20,x+15,y+10),outline='#e2f0f3',width=3)
            draw.text((offset+18,393),'Synthetic motion / shared source poses',font=small,fill='#91a8b2')
        images.append(image)
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True);images[0].save(out,save_all=True,append_images=images[1:],duration=67,loop=0,optimize=True)
    print('PREVIEW_CREATED',out,out.stat().st_size)
if __name__=='__main__':main()
