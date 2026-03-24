import os, json, random, asyncio, subprocess, re, requests, time
import google.generativeai as genai
from edge_tts import Communicate
K, T, I = os.getenv("GEMINI_API_KEY"), os.getenv("INSTA_ACCESS_TOKEN"), os.getenv("INSTA_ACCOUNT_ID")
for f in ['assets', 'templates', 'output']: os.makedirs(f, exist_ok=True)
with open('config.json', 'r') as f: cfg = json.load(f)
genai.configure(api_key=K)
model = genai.GenerativeModel('gemini-1.5-flash')
async def get_s():
    topic = random.choice(cfg['topics'])
    p = f"Create a 15s dark psychology script about {topic}. Return JSON: {{'script': '...', 'caption': '...', 'hashtags': '...'}}."
    try:
        r = model.generate_content(p)
        m = re.search(r'\{.*\}', r.text, re.DOTALL)
        return json.loads(m.group()) if m else json.loads(r.text)
    except: return {"script": "Silence is the best answer to a fool.", "caption": "Silence.", "hashtags": "#psych"}
async def get_v(text):
    p = "assets/voice.mp3"
    await Communicate(text, "en-US-GuyNeural", rate="+12%").save(p)
    d = subprocess.run(["ffprobe","-v","0","-show_entries","format=duration","-of","compact=p=0:nk=1",p], capture_output=True, text=True).stdout
    return p, float(d or 15.0)
def render(data, vp, dur):
    ts = [f for f in os.listdir('templates') if f.endswith('.mp4')]
    vi = ["-stream_loop","-1","-i",f"templates/{random.choice(ts)}"] if ts else ["-f","lavfi","-i","color=c=0x0a0a0a:s=1080x1920:d=1"]
    vf = "vignette=PI/4,zoompan=z='zoom+0.001':d=125:s=1080x1920" if ts else "vignette=PI/3"
    ft = "assets/font.ttf"
    fa = f"fontfile='{ft}':" if os.path.exists(ft) else ""
    ws = re.findall(r"[\w']+", data['script'].upper())
    tpw = dur / len(ws)
    dfs = []
    for i, w in enumerate(ws):
        s, e = i*tpw, (i+1)*tpw
        c = "yellow" if w.lower() in cfg['power_words'] else "white"
        if i==0: c = "red"
        sz = f"if(lt(t,{s}),0,100+40*exp(-15*(t-{s})))"
        cw = w.replace("'","").replace(":","").replace(",","")
        dfs.append(f"drawtext=text='{cw}':{fa}fontcolor={c}:fontsize='{sz}':borderw=4:bordercolor=black:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{s},{e})'")
    ai = ["-i", vp]
    mp, sp = "assets/music.mp3", "assets/sfx.mp3"
    hm, hs = os.path.exists(mp), os.path.exists(sp)
    if hm: ai += ["-i", mp]
    if hs: ai += ["-i", sp]
    am = "[1:a]volume=1.0[va]"
    ls = ["[va]"]
    if hm: am += ";[2:a]volume=0.15[ma]"; ls.append("[ma]")
    if hs: idx = 2+int(hm); am += f";[{idx}:a]volume=0.8[sa]"; ls.append("[sa]")
    fa_str = f"{am};{''.join(ls)}amix=inputs={len(ls)}:duration=first[aout]" if len(ls)>1 else "[1:a]volume=1.0[aout]"
    cmd = ["ffmpeg","-y"] + vi + ai + ["-filter_complex",f"[0:v]{vf},{','.join(dfs)}[vout];{fa_str}","-map","[vout]","-map","[aout]","-t",str(dur),"-c:v","libx264","-preset","superfast","-crf","22","output/final.mp4"]
    subprocess.run(cmd)
def up(path, cap):
    if not T or not I: return
    try:
        u = requests.post("https://catbox.moe/user/api.php",data={'reqtype':'fileupload'},files={'fileToUpload':open(path,'rb')}).text
        r = requests.post(f"https://graph.facebook.com/v19.0/{I}/media",data={'video_url':u,'caption':cap,'media_type':'REELS','access_token':T}).json()
        if 'id' in r:
            time.sleep(45)
            requests.post(f"https://graph.facebook.com/v19.0/{I}/media_publish",data={'creation_id':r['id'],'access_token':T})
    except: pass
async def main():
    d = await get_s()
    vp, dur = await get_v(d['script'])
    render(d, vp, dur)
    if os.path.exists("output/final.mp4"):
        print("✅ SUCCESS")
        up("output/final.mp4", f"{d['caption']}\n\n{d['hashtags']}")
if __name__ == "__main__":
    asyncio.run(main())
