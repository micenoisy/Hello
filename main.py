import os, json, random, asyncio, subprocess, re, requests, time
from edge_tts import Communicate

# [1] SECRETS & PATHS
OR_KEY = os.getenv("OPENROUTER_API_KEY")
for f in ['assets', 'templates', 'output']: os.makedirs(f, exist_ok=True)

def audit():
    print("🔍 --- SYSTEM AUDIT ---")
    f_ok = os.path.exists("assets/font.ttf")
    ts = [f for f in os.listdir('templates') if f.endswith('.mp4')]
    print(f"Font: {'✅' if f_ok else '❌'} | Templates: {len(ts)}")
    return ts

# [2] OPENROUTER AI ENGINE (Reliable & Free)
async def get_script():
    print("🧠 AI: Generating Script via OpenRouter...")
    try:
        with open('config.json', 'r') as f: cfg = json.load(f)
        topic = random.choice(cfg['topics'])
        
        # Calling OpenRouter (Llama 3.1 8B is free and fast)
        res = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OR_KEY}"},
            data=json.dumps({
                "model": "meta-llama/llama-3.1-8b-instruct:free",
                "messages": [{"role": "user", "content": f"Write a 20s dark psychology script about {topic}. Start with a hook. Word-by-word style. Return ONLY JSON: {{'script': '...', 'caption': '...', 'hashtags': '...'}}"}]
            })
        )
        data = res.json()['choices'][0]['message']['content']
        m = re.search(r'\{.*\}', data, re.DOTALL)
        return json.loads(m.group()), cfg
    except Exception as e:
        print(f"⚠️ AI FAIL: {e}. Using Fallback.")
        return {"script": "THE MOST DANGEROUS PERSON WATCHES EVERYTHING. THEY KNOW YOUR MOVE. THIS IS WHY YOU NEVER REVEAL THE TRUTH."}, {"power_words": ["dangerous"]}

# [3] NATURAL VOICE + SILENCE TRIMMING
async def get_audio(text):
    print("🎙️ AUDIO: Generating Natural Voice & Trimming Silence...")
    raw_p, clean_p, b = "assets/raw.mp3", "assets/voice.mp3", []
    # Andrew is a very natural-sounding USA male voice
    c = Communicate(text, "en-US-AndrewNeural", rate="+5%", pitch="+0Hz")
    
    with open(raw_p, "wb") as f:
        async for ck in c.stream():
            if ck["type"] == "audio": f.write(ck["data"])
            elif ck["type"] == "WordBoundary":
                b.append({"w": ck["text"], "s": ck["offset"]/10**7, "e": (ck["offset"]+ck["duration"])/10**7})
    
    # FFmpeg: SLICE SILENCE (Removes any gap longer than 0.1s)
    subprocess.run(["ffmpeg", "-y", "-i", raw_p, "-af", "silenceremove=1:0:-50dB", clean_p], capture_output=True)
    
    with open("assets/subs.json", "w") as f: json.dump(b, f)
    dur = subprocess.run(["ffprobe","-v","0","-show_entries","format=duration","-of","compact=p=0:nk=1",clean_p], capture_output=True, text=True).stdout
    return clean_p, float(dur or 15.0)

# [4] DYNAMIC PRO RENDER (NO ZOOM, STICKY SYNC)
def render(data, cfg, vp, dur, ts):
    print(f"🎬 VIDEO: Rendering {dur}s Reel...")
    if ts:
        vi = ["-stream_loop", "-1", "-i", f"templates/{random.choice(ts)}"]
        vb = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,vignette=PI/4"
    else:
        vi = ["-f", "lavfi", "-i", "color=c=0a0a0a:s=1080x1920:d=1"]
        vb = "vignette=PI/3"
    
    with open("assets/subs.json", "r") as f: bd = json.load(f)
    font = f"fontfile='assets/font.ttf':" if os.path.exists("assets/font.ttf") else ""
    draw = []
    
    for i, it in enumerate(bd):
        s, e, w = it["s"], it["e"], it["w"].upper().replace("'", "").replace(".", "")
        cl = "yellow" if any(pw.lower() in w.lower() for pw in cfg.get('power_words', [])) else "white"
        if i == 0: cl = "red"
        # Hormozi Pop Animation
        sz = f"if(lt(t,{s}),0,if(lt(t,{s}+0.06),170,140))"
        # Shadow + Main Text
        draw.append(f"drawtext=text='{w}':{font}fontcolor=black@0.9:fontsize='{sz}+15':x=(w-text_w)/2+8:y=(h-text_h)/2+8:enable='between(t,{s},{e})'")
        draw.append(f"drawtext=text='{w}':{font}fontcolor={cl}:fontsize='{sz}':x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{s},{e})'")

    v_filt = f"[0:v]{vb}"
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
    if os.path.exists("output/final.mp4"): print(f"✅ SUCCESS: Reel ready ({round(dur, 2)}s)")

if __name__ == "__main__":
    asyncio.run(main())
