"""Build an equal-framing, full-rate comparison from maintainer-provided clips."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
import cv2,numpy as np
from PIL import Image

def main():
    p=argparse.ArgumentParser();p.add_argument('--original',required=True);p.add_argument('--density',required=True);p.add_argument('--output',default='docs/media');args=p.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    paths=[Path(args.original),Path(args.density)];caps=[cv2.VideoCapture(str(path)) for path in paths]
    assert all(c.isOpened() for c in caps)
    counts=[round(c.get(cv2.CAP_PROP_FRAME_COUNT)) for c in caps];rates=[c.get(cv2.CAP_PROP_FPS) for c in caps]
    assert counts[0]==counts[1] and counts[0]>0 and all(abs(r-30)<.01 for r in rates),'Expected equal 30 fps clips'
    bounds=[]
    while True:
        ok,im=caps[0].read()
        if not ok:break
        hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV);ys,xs=np.where((hsv[:,:,1]>50)|(hsv[:,:,2]<110))
        if len(xs):bounds.append((xs.min(),ys.min(),xs.max(),ys.max()))
    assert bounds;bounds=np.array(bounds);w=round(caps[0].get(cv2.CAP_PROP_FRAME_WIDTH));h=round(caps[0].get(cv2.CAP_PROP_FRAME_HEIGHT))
    x0=max(0,int(bounds[:,0].min())-25);y0=max(0,int(bounds[:,1].min())-25);x1=min(w,int(bounds[:,2].max())+26);y1=min(h,int(bounds[:,3].max())+26)
    panel_w=460;panel_h=round((y1-y0)/(x1-x0)*panel_w/2)*2;total_h=panel_h+50
    for cap in caps:cap.set(cv2.CAP_PROP_POS_FRAMES,0)
    command=['ffmpeg','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'920x{total_h}','-r','30','-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','16','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'original-vs-density.mp4')]
    images=[]
    with open(out/'showcase_encode.log','w') as log:
        process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log)
        for f in range(counts[0]):
            canvas=np.full((total_h,920,3),24,dtype=np.uint8)
            for i,(cap,label) in enumerate(zip(caps,['ORIGINAL - SMOOTH','CHARM - DENSITY'])):
                ok,im=cap.read();assert ok
                canvas[50:,i*460:(i+1)*460]=cv2.resize(im[y0:y1,x0:x1],(panel_w,panel_h),interpolation=cv2.INTER_LANCZOS4)
                cv2.putText(canvas,label,(i*460+16,32),cv2.FONT_HERSHEY_SIMPLEX,.65,(220,240,230),1,cv2.LINE_AA)
            process.stdin.write(canvas.tobytes())
            images.append(Image.fromarray(cv2.cvtColor(canvas,cv2.COLOR_BGR2RGB)))
        process.stdin.close();assert process.wait(timeout=120)==0
    for cap in caps:cap.release()
    # Full-resolution true-color animation, avoiding GIF palette banding/downscaling.
    images[0].save(out/'original-vs-density.webp',format='WEBP',save_all=True,append_images=images[1:],duration=[33 if i%3!=2 else 34 for i in range(len(images))],loop=0,quality=94,method=4)
    records={}
    for path,name in zip(paths,['original-smooth.mp4','density-retimed.mp4']):
        shutil.copy2(path,out/name);records[name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'frames':counts[0],'fps':30}
    (out/'showcase.json').write_text(json.dumps({'inputs':records,'comparison_crop_xyxy':[x0,y0,x1,y1],'same_crop_for_both_panels':True,'pose_changes':False,'output_size':[920,total_h]},indent=2))
    for name in ('original-smooth.mp4','density-retimed.mp4','original-vs-density.mp4'):
        info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=nb_frames,r_frame_rate','-of','json',str(out/name)]))['streams'][0]
        assert info['nb_frames']==str(counts[0]) and info['r_frame_rate']=='30/1'
    print('SHOWCASE_VERIFIED',counts[0],'frames; original/density inputs copied byte-for-byte')
if __name__=='__main__':main()
