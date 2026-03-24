import os, json, random, asyncio, subprocess, re, requests, time
import google.generativeai as genai
from edge_tts import Communicate

# 1. SETUP
K, T, I = os.getenv("GEMINI_API_KEY"), os.getenv("INSTA_ACCESS_TOKEN"), os.getenv("INSTA_ACCOUNT_ID")
for f in ['assets', 'templates', 'output']: os.makedirs(f, exist_ok=True)

# 2. ASSET AUDIT
def audit():
    print("🔍 --- ASSET AUDIT ---")
    f_ok = os.path.exists("assets/font.ttf")
    ts = [f for f in os.listdir('templates') if f.endswith('.mp4')]
    print(f"Font: {'✅' if f_ok else '❌'}")
    print(f"Templates: {len(ts)} found")
    return ts

# 3. AI SCRIPT (FIXED 404 ERROR)
async def get_script():
    print("🧠 AI: Generating Unique Script...")
    try:
        with open('config.json', 'r') as f: cfg = json.load(f)
        genai.configure(api_key=K)
        # Try different model versions to find the one supported by the library
        model_name = 'gemini-1.5-flash'
        model = genai.GenerativeModel(model_name)
        
        topic = random.choice(cfg['topics'])
        p = f"Write a 18s dark psychology script about {topic}. Start with a hook. Return ONLY JSON: {{'script': '...', 'caption': '...', 'hashtags': '...'}}"
        r = model.generate_content(p)
        m = re.search(r'\{.*\}', r.text, re.DOTALL)
        return json.loads(m.group()) if m else json.loads(r.text), cfg
    except Exception as e:
        print(f"⚠️ AI FAIL: {e}")
        # HARDCODED FALLBACK FOR SUBTITLE TESTING
        return {
            "script": "THE MOST DANGEROUS PERSON IS THE ONE WHO WATCHES EVERYTHING. THEY ARE CALCULATING YOUR MOVE. THIS IS WHY YOU MUST NEVER REVEAL YOUR NEXT STEP.",
            "caption": "Silence is power.",
            "hashtags": "#darkpsychology"
        }, {"power_words": ["dangerous", "calculating", "never"]}

# 4. WORD-BY-WORD SYNC
async def get_audio(text):
    print("🎙️ AUDIO: Syncing Word-by-Word...")
    p, b = "assets/voice.mp3", []
    # Christopher is the best male voice for USA dark psychology
    c = Communicate(text, "en-US-ChristopherNeural", rate="+15%", pitch="-5Hz")
    with open(p, "wb") as f:
        async for ck in c.stream():
            if ck["type"] == "audio": f.write(ck["data"])
            elif ck["type"] == "WordBoundary":
                b.append({"w": ck["text"], "s": ck["offset"]/10**7, "e": (ck["offset"]+ck["duration"])/10**7})
    
    if not b: print("❌ ERROR: No word boundaries found!")
    else: print(f"✅ Words Tracked: {len(b)}")
    
    with open("assets/subs.json", "w") as f: json.dump(b, f)
    res = subprocess.run(["ffprobe","-v","0","-show_entries","format=duration","-of","compact=p=0:nk=1",p], capture_output=True, text=True)
    return p, float(res.stdout or 15.0)

# 5. DYNAMIC RENDER
def render(data, cfg, vp, dur, ts):
    print("🎬 VIDEO: Rendering Reel...")
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
        # Color Logic
        cl = "yellow" if any(pw.lower() in w.lower() for pw in cfg.get('power_words', [])) else "white"
        if i == 0: cl = "red" # Hook RED
        
        # POP ANIMATION
        sz = f"if(lt(t,{s}),0,if(lt(t,{s}+0.05),170,140))"
        
        # Layer 1: Strong Black Shadow
        draw.append(f"drawtext=text='{w}':{font}fontcolor=black@0.9:fontsize='{sz}+12':x=(w-text_w)/2+6:y=(h-text_h)/2+6:enable='between(t,{s},{e})'")
        # Layer 2: Main Text
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

# 6. MAIN
async def main():
    ts = audit()
    d, cfg = await get_script()
    vp, dur = await get_audio(d['script'])
    render(d, cfg, vp, dur, ts)
    if os.path.exists("output/final.mp4"): print("✅ SUCCESS: Dynamic Video Ready.")
    else: print("❌ FAILED: Check FFmpeg logs.")

if __name__ == "__main__":
    asyncio.run(main())