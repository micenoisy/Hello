import os, json, random, asyncio, subprocess, re, requests, time
import google.generativeai as genai
from edge_tts import Communicate

# [STEP 1] ENVIRONMENT SETUP
K, T, I = os.getenv("GEMINI_API_KEY"), os.getenv("INSTA_ACCESS_TOKEN"), os.getenv("INSTA_ACCOUNT_ID")
for f in ['assets', 'templates', 'output']: os.makedirs(f, exist_ok=True)

def audit():
    print("🔍 --- ASSET STATUS REPORT ---")
    has_f = os.path.exists("assets/font.ttf")
    has_m = os.path.exists("assets/music.mp3")
    tmps = [f for f in os.listdir('templates') if f.endswith('.mp4')]
    print(f"{'✅' if has_f else '❌'} FONT: assets/font.ttf")
    print(f"{'✅' if has_m else '❌'} MUSIC: assets/music.mp3")
    print(f"{'✅' if tmps else '❌'} TEMPLATES: {len(tmps)} found")
    print("------------------------------")
    return tmps

# [STEP 2] AI SCRIPT GENERATION
async def get_script():
    print("🧠 AI: Creating Unique Script...")
    try:
        with open('config.json', 'r') as f: cfg = json.load(f)
        genai.configure(api_key=K)
        model = genai.GenerativeModel('gemini-1.5-flash')
        p = f"Write a 18s dark psychology script about {random.choice(cfg['topics'])}. Hook, 3 short facts, loop. Return ONLY JSON: {{'script': '...', 'caption': '...', 'hashtags': '...'}}"
        r = model.generate_content(p)
        m = re.search(r'\{.*\}', r.text, re.DOTALL)
        return json.loads(m.group()) if m else json.loads(r.text), cfg
    except Exception as e:
        print(f"⚠️ AI FAIL: {e}")
        return {"script": "THE QUIETEST PERSON IN THE ROOM IS THE MOST DANGEROUS. THEY WATCH EVERYTHING. THEY KNOW YOUR MOVE. THIS IS WHY..."}, {"power_words": ["dangerous"]}

# [STEP 3] WORD-BY-WORD AUDIO SYNC
async def get_audio(text):
    print("🎙️ AUDIO: Syncing Voiceover...")
    p, b = "assets/voice.mp3", []
    c = Communicate(text, "en-US-ChristopherNeural", rate="+15%", pitch="-5Hz")
    with open(p, "wb") as f:
        async for ck in c.stream():
            if ck["type"] == "audio": f.write(ck["data"])
            elif ck["type"] == "WordBoundary":
                b.append({"w": ck["text"], "s": ck["offset"]/10**7, "e": (ck["offset"]+ck["duration"])/10**7})
    with open("assets/subs.json", "w") as f: json.dump(b, f)
    d = subprocess.run(["ffprobe","-v","0","-show_entries","format=duration","-of","compact=p=0:nk=1",p], capture_output=True, text=True).stdout
    return p, float(d or 15.0)

# [STEP 4] DYNAMIC RENDER (WORD-BY-WORD)
def render(data, cfg, vp, dur, tmps):
    print("🎬 VIDEO: Rendering Hormozi-Style Subtitles...")
    if tmps:
        v_in = ["-stream_loop", "-1", "-i", f"templates/{random.choice(tmps)}"]
        v_f = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,vignette=PI/4"
    else:
        v_in = ["-f", "lavfi", "-i", "color=c=0x0a0a0a:s=1080x1920:d=1"]
        v_f = "vignette=PI/3"
    
    with open("assets/subs.json", "r") as f: bd = json.load(f)
    font = "fontfile='assets/font.ttf':" if os.path.exists("assets/font.ttf") else ""
    draw = []
    
    for i, it in enumerate(bd):
        s, e, w = it["s"], it["e"], it["w"].upper().replace("'", "")
        cl = "yellow" if any(pw.lower() in w.lower() for pw in cfg.get('power_words', [])) else "white"
        if i == 0: cl = "red"
        # Micro-sync Pop logic
        sz = f"if(lt(t,{s}),0,if(lt(t,{s}+0.06),160,135))"
        # Layer 1: Heavy Shadow Glow
        draw.append(f"drawtext=text='{w}':{font}fontcolor=black@0.8:fontsize='{sz}+12':x=(w-text_w)/2+6:y=(h-text_h)/2+6:enable='between(t,{s},{e})'")
        # Layer 2: Main Text
        draw.append(f"drawtext=text='{w}':{font}fontcolor={cl}:fontsize='{sz}':x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{s},{e})'")

    ai = ["-i", vp]
    mp = "assets/music.mp3"
    if os.path.exists(mp):
        ai += ["-i", mp]
        am = "[1:a]volume=1.5[va];[2:a]volume=0.2[ma];[va][ma]amix=inputs=2:duration=first,loudnorm[aout]"
    else: am = "[1:a]volume=1.5,loudnorm[aout]"

    cmd = ["ffmpeg", "-y"] + v_in + ai + ["-filter_complex", f"[0:v]{v_f},{','.join(draw)}[vout];{am}", "-map", "[vout]", "-map", "[aout]", "-t", str(dur), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "output/final.mp4"]
    subprocess.run(cmd)

# [STEP 5] MAIN LOOP
async def main():
    tmps = audit()
    d, cfg = await get_script()
    vp, dur = await get_audio(d['script'])
    render(d, cfg, vp, dur, tmps)
    if os.path.exists("output/final.mp4"): print("✅ SUCCESS: Reel Generated.")

if __name__ == "__main__":
    asyncio.run(main())        "-filter_complex", f"{filter_complex};{a_mix}",
        "-map", "[vout]", "-map", "[aout]", "-t", str(duration),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "output/final.mp4"
    ]
    subprocess.run(cmd, capture_output=True)

# 5. MAIN
async def main():
    has_t = audit_assets()
    data, cfg = await generate_script()
    voice_file, duration = await generate_audio(data['script'])
    render_video(data, cfg, voice_file, duration, has_t)
    
    if os.path.exists("output/final.mp4"):
        print("✅ SUCCESS: Dynamic Video Ready.")

if __name__ == "__main__":
    asyncio.run(main())        
        # Clean static subtitles (No disgusting zoom)
        # We use a slight font size 'pop' only at the start of the phrase
        size = f"if(lt(t,{t_start}),0,if(lt(t,{t_start}+0.08),140,130))"
        
        # Shadow + Main Text for high readability
        draw_filters.append(f"drawtext=text='{phrase}':{f_arg}fontcolor=black@0.8:fontsize='{size}+10':x=(w-text_w)/2+5:y=(h-text_h)/2+5:enable='between(t,{t_start},{t_end})'")
        draw_filters.append(f"drawtext=text='{phrase}':{f_arg}fontcolor={color}:fontsize='{size}':x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{t_start},{t_end})'")

    filter_complex = f"[0:v]{v_base}"
    if draw_filters: filter_complex += "," + ",".join(draw_filters)
    filter_complex += "[vout]"

    # Audio Mix
    m_path = "assets/music.mp3"
    a_ins = ["-i", voice_path]
    if os.path.exists(m_path):
        a_ins += ["-i", m_path]
        a_mix = "[1:a]volume=1.5[va];[2:a]volume=0.2[ma];[va][ma]amix=inputs=2:duration=first,loudnorm[aout]"
    else:
        a_mix = "[1:a]volume=1.5,loudnorm[aout]"

    cmd = ["ffmpeg", "-y"] + v_in + a_ins + [
        "-filter_complex", f"{filter_complex};{a_mix}",
        "-map", "[vout]", "-map", "[aout]", "-t", str(duration),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "output/final.mp4"
    ]
    
    subprocess.run(cmd, capture_output=True)

# 6. MAIN EXECUTION
async def main():
    print("🚀 AGENT STARTING...")
    templates = audit_assets()
    
    data, cfg = await get_script()
    voice_file, duration = await get_audio(data['script'])
    
    render_video(data, cfg, voice_file, duration, templates)
    
    if os.path.exists("output/final.mp4"):
        print(f"✅ SUCCESS: Video generated successfully.")
    else:
        print("❌ FAILED: Final video not found. Check FFmpeg logs.")

if __name__ == "__main__":
    asyncio.run(main())
