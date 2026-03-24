import os, json, random, asyncio, subprocess, re, requests, time
import google.generativeai as genai
from edge_tts import Communicate

# 1. SETUP
K, T, I = os.getenv("GEMINI_API_KEY"), os.getenv("INSTA_ACCESS_TOKEN"), os.getenv("INSTA_ACCOUNT_ID")
for f in ['assets', 'templates', 'output']: os.makedirs(f, exist_ok=True)

# 2. AUDIT
def audit():
    print("🔍 --- SYSTEM AUDIT ---")
    f_ok = os.path.exists("assets/font.ttf")
    ts = [f for f in os.listdir('templates') if f.endswith('.mp4')]
    print(f"Font: {'✅' if f_ok else '❌'} | Templates: {len(ts)}")
    return ts

# 3. AI SCRIPT (FIXED FOR STABILITY)
async def get_script():
    print("🧠 AI: Generating unique script...")
    try:
        with open('config.json', 'r') as f: cfg = json.load(f)
        genai.configure(api_key=K)
        # Using the direct model name for v1 stable API
        model = genai.GenerativeModel('gemini-1.5-flash')
        topic = random.choice(cfg['topics'])
        p = f"Write a 18s dark psychology script about {topic}. Aggressive hook. Short words. Return ONLY JSON: {{'script': '...', 'caption': '...', 'hashtags': '...'}}"
        r = model.generate_content(p)
        m = re.search(r'\{.*\}', r.text, re.DOTALL)
        return json.loads(m.group()), cfg
    except Exception as e:
        print(f"⚠️ AI FAIL ({e}): Using Fallback.")
        return {"script": "THE MOST DANGEROUS PERSON WATCHES EVERYTHING. THEY KNOW YOUR MOVE. THIS IS WHY YOU NEVER REVEAL THE TRUTH."}, {"power_words": ["dangerous"]}

# 4. WORD-BY-WORD SYNC (FIXED STREAM LISTENER)
async def get_audio(text):
    print("🎙️ AUDIO: Syncing Micro-timestamps...")
    p, b = "assets/voice.mp3", []
    c = Communicate(text, "en-US-ChristopherNeural", rate="+15%", pitch="-5Hz")
    
    with open(p, "wb") as f:
        async for chunk in c.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # Ensure we are capturing every word exactly
                b.append({
                    "w": chunk["text"], 
                    "s": chunk["offset"] / 10**7, 
                    "e": (chunk["offset"] + chunk["duration"]) / 10**7
                })
    
    if not b:
        print("❌ ERROR: Word Boundaries failed. Retrying with simpler text...")
        # Emergency word splitter if stream fails
        words = text.split()
        dur_est = 15.0 # Rough estimate
        for i, w in enumerate(words):
            b.append({"w": w, "s": i*(dur_est/len(words)), "e": (i+1)*(dur_est/len(words))})

    with open("assets/subs.json", "w") as f: json.dump(b, f)
    res = subprocess.run(["ffprobe","-v","0","-show_entries","format=duration","-of","compact=p=0:nk=1",p], capture_output=True, text=True)
    return p, float(res.stdout or 15.0)

# 5. DYNAMIC RENDER (WORD-BY-WORD)
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
        cl = "yellow" if any(pw.lower() in w.lower() for pw in cfg.get('power_words', [])) else "white"
        if i == 0: cl = "red" # Hook RED
        
        # Word-by-word POP animation
        sz = f"if(lt(t,{s}),0,if(lt(t,{s}+0.06),170,140))"
        
        # Shadow Glow Layer
        draw.append(f"drawtext=text='{w}':{font}fontcolor=black@0.9:fontsize='{sz}+12':x=(w-text_w)/2+6:y=(h-text_h)/2+6:enable='between(t,{s},{e})'")
        # Main Text Layer
        draw.append(f"drawtext=text='{w}':{font}fontcolor={cl}:fontsize='{sz}':x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{s},{e})'")

    v_filt = f"[0:v]{vf}"
    if draw: v_filt += "," + ",".join(draw)
    v_filt += "[vout]"

 