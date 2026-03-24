import os, json, random, asyncio, subprocess, re, requests, time
from google import genai
from edge_tts import Communicate

# [1] SECRETS & PATHS
K = os.getenv("GEMINI_API_KEY") # Ensure this is correct in Secrets
T = os.getenv("INSTA_ACCESS_TOKEN")
I = os.getenv("INSTA_ACCOUNT_ID")

for f in ['assets', 'templates', 'output']: os.makedirs(f, exist_ok=True)

def audit():
    print("🔍 --- SYSTEM PERFORMANCE AUDIT ---")
    f_ok = os.path.exists("assets/font.ttf")
    m_ok = os.path.exists("assets/music.mp3")
    ts = [f for f in os.listdir('templates') if f.endswith('.mp4')]
    print(f"Font: {'✅' if f_ok else '❌'} | Music: {'✅' if m_ok else '❌'} | Templates: {len(ts)}")
    return ts

# [2] STABLE AI ENGINE (Gemini 1.5 Flash Stable)
async def get_script():
    print("🧠 AI: Generating unique psychological script...")
    try:
        with open('config.json', 'r') as f: cfg = json.load(f)
        # Using the standard SDK client correctly
        client = genai.Client(api_key=K)
        topic = random.choice(cfg['topics'])
        p = f"Write a 20s dark psychology script about {topic}. Start with 'THEY DON'T WANT YOU TO KNOW...' or similar. Aggressive. Return ONLY JSON: {{'script': '...', 'caption': '...', 'hashtags': '...'}}"
        r = client.models.generate_content(model="gemini-1.5-flash", contents=p)
        m = re.search(r'\{.*\}', r.text, re.DOTALL)
        return json.loads(m.group()), cfg
    except Exception as e:
        print(f"⚠️ AI FAIL: {e}")
        return {"script": "THE REASON THEY HIDE THEIR TRUTH IS BECAUSE THEY ARE AFRAID OF YOUR POWER. NEVER REVEAL YOUR NEXT MOVE. REMEMBER THIS."}, {"power_words": ["power", "truth", "never"]}

# [3] MICRO-SYNC WORD ENGINE
async def get_audio(text):
    print("🎙️ AUDIO: Generating Word-Level Sync...")
    p, b = "assets/voice.mp3", []
    # Christopher is the #1 voice for Dark Psychology
    c = Communicate(text, "en-US-ChristopherNeural", rate="+15%", pitch="-8Hz")
    with open(p, "wb") as f:
        async for ck in c.stream():
            if ck["type"] == "audio": f.write(ck["data"])
            elif ck["type"] == "WordBoundary":
                b.append({"w": ck["text"], "s": ck["offset"]/10**7, "e": (ck["offset"]+ck["duration"])/10**7})
    with open("assets/subs.json", "w") as f: json.dump(b, f)
    d = subprocess.run(["ffprobe","-v","0","-show_entries","format=duration","-of","compact=p=0:nk=1",p], capture_output=True, text=True).stdout
    return p, float(d or 15.0)

# [4] PRO SUBTITLE RENDER (GLOW + STROKE)
def render(data, cfg, vp, dur, ts):
    print("🎬 VIDEO: Rendering Pro-Style Reel...")
    if ts:
        vi = ["-stream_loop", "-1", "-i", f"templates/{random.choice(ts)}"]
        # Subtle pulsing movement (Visual Heartbeat)
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,vignette=PI/4"
    else:
        vi = ["-f", "lavfi", "-i", "color=c=0x0a0a0a:s=1080x1920:d=1"]
        vf = "vignette=PI/3"
    
    with open("assets/subs.json", "r") as f: bd = json.load(f)
    font = f"fontfile='assets/font.ttf':" if os.path.exists("assets/font.ttf") else ""
    draw = []
    
    for i, it in enumerate(bd):
        s, e, w = it["s"], it["e"], it["w"].upper().replace("'", "")
        cl = "yellow" if any(pw.lower() in w.lower() for pw in cfg.get('power_words', [])) else "white"
        if i == 0: cl = "red"
        
        # Hormozi Pop Animation (Size 170 to 140)
        sz = f"if(lt(t,{s}),0,if(lt(t,{s}+0.06),170,140))"
        
        # [STACKED RENDERING FOR GLOW]
        # Layer 1: Thick Black Outer Stroke
        draw.append(f"drawtext=text='{w}':{font}fontcolor=black@0.9:fontsize='{sz}+18':borderw=10:bordercolor=black:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{s},{e})'")
        # Layer 2: Colored Inner Glow
        draw.append(f"drawtext=text='{w}':{font}fontcolor={cl}:fontsize='{sz}':x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{s},{e})'")

    ai = ["-i", vp]
    mp = "assets/music.mp3"
    if os.path.exists(mp):
        ai += ["-i", mp]
        am = "[1:a]volume=1.8[va];[2:a]volume=0.25[ma];[va][ma]amix=inputs=2:duration=first,loudnorm[aout]"
    else: am = "[1:a]volume=1.8,loudnorm[aout]"

    cmd = ["ffmpeg", "-y"] + vi + ai + ["-filter_complex", f"[0:v]{vf},{','.join(draw)}[vout];{am}", "-map", "[vout]", "-map", "[aout]", "-t", str(dur), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "output/final.mp4"]
    subprocess.run(cmd)

async def main():
    ts = audit()
    d, cfg = await get_script()
    vp, dur = await get_audio(d['script'])
    render(d, cfg, vp, dur, ts)
    if os.path.exists("output/final.mp4"): print(f"✅ SUCCESS: Reel ready ({round(dur, 2)}s)")

if __name__ == "__main__":
    asyncio.run(main())
