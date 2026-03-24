import os, json, random, asyncio, subprocess, re, requests, time
from google import genai
from edge_tts import Communicate

# [1] SECRETS & SETUP
API_KEY = os.getenv("GOOGLE_API_KEY")
INSTA_TOKEN = os.getenv("INSTA_ACCESS_TOKEN")
INSTA_ID = os.getenv("INSTA_ACCOUNT_ID")

for f in ['assets', 'templates', 'output']: os.makedirs(f, exist_ok=True)

def audit():
    print("🔍 --- SYSTEM AUDIT ---")
    f_ok = os.path.exists("assets/font.ttf")
    m_ok = os.path.exists("assets/music.mp3")
    ts = [f for f in os.listdir('templates') if f.endswith('.mp4')]
    print(f"Font: {'✅' if f_ok else '❌'} | Music: {'✅' if m_ok else '❌'} | Templates: {len(ts)}")
    return ts

# [2] NEW AI ENGINE (GEMINI 2.0 / 1.5 FLASH)
async def get_script():
    print("🧠 AI: Generating High-Performance Script...")
    try:
        with open('config.json', 'r') as f: cfg = json.load(f)
        client = genai.Client(api_key=API_KEY)
        topic = random.choice(cfg['topics'])
        
        prompt = f"Write a 15-20s viral Dark Psychology script about {topic}. Aggressive hook. Word-by-word style. Return ONLY JSON: {{'script': '...', 'caption': '...', 'hashtags': '...'}}"
        
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        m = re.search(r'\{.*\}', response.text, re.DOTALL)
        data = json.loads(m.group())
        print(f"✅ AI SCRIPT SUCCESS: {topic}")
        return data, cfg
    except Exception as e:
        print(f"⚠️ AI ERROR: {e}. Using Fallback.")
        return {"script": "THE MOST DANGEROUS PERSON WATCHES EVERYTHING. THEY ARE CALCULATING YOUR MOVE. THIS IS WHY YOU NEVER REVEAL THE TRUTH."}, {"power_words": ["dangerous"]}

# [3] WORD-BY-WORD MICRO-SYNC
async def get_audio(text):
    print("🎙️ AUDIO: Syncing Word-by-Word...")
    p, b = "assets/voice.mp3", []
    c = Communicate(text, "en-US-ChristopherNeural", rate="+15%", pitch="-5Hz")
    
    with open(p, "wb") as f:
        async for ck in c.stream():
            if ck["type"] == "audio": f.write(ck["data"])
            elif ck["type"] == "WordBoundary":
                b.append({"w": ck["text"], "s": ck["offset"]/10**7, "e": (ck["offset"]+ck["duration"])/10**7})
    
    with open("assets/subs.json", "w") as f: json.dump(b, f)
    res = subprocess.run(["ffprobe","-v","0","-show_entries","format=duration","-of","compact=p=0:nk=1",p], capture_output=True, text=True)
    return p, float(res.stdout or 15.0)

# [4] DYNAMIC PRO RENDER
def render(data, cfg, vp, dur, ts):
    print("🎬 VIDEO: Rendering Word-by-Word Reels...")
    if ts:
        vi = ["-stream_loop", "-1", "-i", f"templates/{random.choice(ts)}"]
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,vignette=PI/4"
    else:
        vi = ["-f", "lavfi", "-i", "color=c=0x0a0a0a:s=1080x1920:d=1"]
        vf = "vignette=PI/3"
    
    with open("assets/subs.json", "r") as f: bd = json.load(f)
    font = "fontfile='assets/font.ttf':" if os.path.exists("assets/font.ttf") else ""
    draw = []
    
    for i, it in enumerate(bd):
        s, e, w = it["s"], it["e"], it["w"].upper().replace("'", "").replace(".", "")
        cl = "yellow" if any(pw.lower() in w.lower() for pw in cfg.get('power_words', [])) else "white"
        if i == 0: cl = "red" # Hook is Red
        
        # Hormozi Pop Animation
        sz = f"if(lt(t,{s}),0,if(lt(t,{s}+0.06),175,140))"
        
        # Layer 1: Strong Black Glow
        draw.append(f"drawtext=text='{w}':{font}fontcolor=black@0.9:fontsize='{sz}+15':x=(w-text_w)/2+8:y=(h-text_h)/2+8:enable='between(t,{s},{e})'")
        # Layer 2: Main Bold Text
        draw.append(f"drawtext=text='{w}':{font}fontcolor={cl}:fontsize='{sz}':x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{s},{e})'")

    v_filt = f"[0:v]{vf}"
    if draw: v_filt += "," + ",".join(draw)
    v_filt += "[vout]"

    ai = ["-i", vp]
    mp = "assets/music.mp3"
    if os.path.exists(mp):
        ai += ["-i", mp]
        am = "[1:a]volume=1.5[va];[2:a]volume=0.2[ma];[va][ma]amix=inputs=2:duration=first,loudnorm[aout]"
    else: am = "[1:a]volume=1.5,loudnorm[aout]"

    cmd = ["ffmpeg", "-y"] + vi + ai + ["-filter_complex", f"{v_filt};{am}", "-map", "[vout]", "-map", "[aout]", "-t", str(dur), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "output/final.mp4"]
    subprocess.run(cmd)

async def main():
    ts = audit()
    d, cfg = await get_script()
    vp, dur = await get_audio(d['script'])
    render(d, cfg, vp, dur, ts)
    if os.path.exists("output/final.mp4"): 
        print(f"✅ SUCCESS: Reel ready ({round(dur, 2)}s)")

if __name__ == "__main__":
    asyncio.run(main())
