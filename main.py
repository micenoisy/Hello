import os, json, random, asyncio, subprocess, re, requests, time
import google.generativeai as genai
from edge_tts import Communicate

# 🔐 API Setup
K, T, I = os.getenv("GEMINI_API_KEY"), os.getenv("INSTA_ACCESS_TOKEN"), os.getenv("INSTA_ACCOUNT_ID")
for f in ['assets', 'templates', 'output']: os.makedirs(f, exist_ok=True)
with open('config.json', 'r') as f: cfg = json.load(f)
genai.configure(api_key=K)
model = genai.GenerativeModel('gemini-1.5-flash')

async def get_s():
    topic = random.choice(cfg['topics'])
    # Precise prompt for a 12-second high-retention loop
    p = f"Write a 12-second dark psychology script about {topic}. Start with a massive hook like 'IF THEY DO THIS...' or 'NEVER TRUST...'. 3 short lines total. The last word must loop perfectly to the first word. Return ONLY JSON: {{'script': '...', 'caption': '...', 'hashtags': '...'}}."
    try:
        r = model.generate_content(p)
        m = re.search(r'\{.*\}', r.text, re.DOTALL)
        return json.loads(m.group())
    except: return {"script": "NEVER REVEAL EVERYTHING. PEOPLE WILL USE YOUR TRUTH TO DESTROY YOUR", "caption": "The power of silence.", "hashtags": "#psychology"}

async def get_v(text):
    p = "assets/voice.mp3"
    await Communicate(text, "en-US-GuyNeural", rate="+15%", pitch="-5Hz").save(p)
    d = subprocess.run(["ffprobe","-v","0","-show_entries","format=duration","-of","compact=p=0:nk=1",p], capture_output=True, text=True).stdout
    return p, float(d or 12.0)

def render(data, vp, dur):
    ts = [f for f in os.listdir('templates') if f.endswith('.mp4')]
    # 🎥 High-End Background Logic
    if ts:
        vi = ["-stream_loop","-1","-i",f"templates/{random.choice(ts)}"]
        vf = "vignette=PI/4,zoompan=z='zoom+0.001':d=125:s=1080x1920"
    else:
        # If no video, create a 'Hypnotic Dark Mist' background using math
        vi = ["-f","lavfi","-i","nullsrc=s=1080x1920:d=1"]
        vf = "geq=lum='10+10*sin(X/20+T)*sin(Y/20+T)':cb=128:cr=128,vignette=PI/3"

    ft = "assets/font.ttf"
    fa = f"fontfile='{ft}':" if os.path.exists(ft) else ""
    
    # ✍️ Advanced Subtitle Logic (Big, Bold, Glow)
    ws = re.findall(r"[\w']+", data['script'].upper())
    tpw = dur / len(ws)
    dfs = []
    for i, w in enumerate(ws):
        s, e = i*tpw, (i+1)*tpw
        c = "yellow" if w.lower() in cfg['power_words'] else "white"
        if i == 0: c = "red" # Hook is Red
        
        # Pop Animation Math
        sz = f"if(lt(t,{s}),0,130+50*exp(-18*(t-{s})))"
        cw = w.replace("'","").replace(":","")
        
        # Stacked Drawtext: 1. Shadow, 2. Main Text (Creates a "Glow/High Contrast" look)
        dfs.append(f"drawtext=text='{cw}':{fa}fontcolor=black:fontsize='{sz}+4':x=(w-text_w)/2+4:y=(h-text_h)/2+4:enable='between(t,{s},{e})'")
        dfs.append(f"drawtext=text='{cw}':{fa}fontcolor={c}:fontsize='{sz}':x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{s},{e})'")

    ai = ["-i", vp]
    mp, sp = "assets/music.mp3", "assets/sfx.mp3"
    hm, hs = os.path.exists(mp), os.path.exists(sp)
    if hm: ai += ["-i", mp]
    if hs: ai += ["-i", sp]
    
    # 🔊 Professional Audio Mix
    am = "[1:a]volume=1.2[va]" # Voice boosted
    ls = ["[va]"]
    if hm: am += ";[2:a]volume=0.2[ma]"; ls.append("[ma]")
    if hs: idx = 2+int(hm); am += f";[{idx}:a]volume=0.9[sa]"; ls.append("[sa]")
    
    fa_str = f"{am};{''.join(ls)}amix=inputs={len(ls)}:duration=first,compressor=threshold=-20dB:ratio=4[aout]" if len(ls)>1 else "[1:a]volume=1.2[aout]"

    cmd = ["ffmpeg","-y"] + vi + ai + ["-filter_complex",f"[0:v]{vf},{','.join(dfs)}[vout];{fa_str}","-map","[vout]","-map","[aout]","-t",str(dur),"-c:v","libx264","-preset","superfast","-crf","20","output/final.mp4"]
    subprocess.run(cmd)

def up(path, cap):
    if not T or not I: return
    try:
        u = requests.post("https://catbox.moe/user/api.php",data={'reqtype':'fileupload'},files={'fileToUpload':open(path,'rb')}).text
        r = requests.post(f"https://graph.facebook.com/v19.0/{I}/media",data={'video_url':u,'caption':cap,'media_type':'REELS','access_token':T}).json()
        if 'id' in r:
            time.sleep(40)
            requests.post(f"https://graph.facebook.com/v19.0/{I}/media_publish",data={'creation_id':r['id'],'access_token':T})
    except: pass

async def main():
    print("🔥 Generating Viral Content...")
    d = await get_s()
    vp, dur = await get_v(d['script'])
    render(d, vp, dur)
    if os.path.exists("output/final.mp4"):
        print("✅ VIDEO READY")
        up("output/final.mp4", f"{d['caption']}\n\n{d['hashtags']}")

if __name__ == "__main__":
    asyncio.run(main())
