import os, json, random, asyncio, subprocess, re, requests, time
import google.generativeai as genai
from edge_tts import Communicate

K, T, I = os.getenv("GEMINI_API_KEY"), os.getenv("INSTA_ACCESS_TOKEN"), os.getenv("INSTA_ACCOUNT_ID")
for f in ['assets', 'templates', 'output']: os.makedirs(f, exist_ok=True)

def audit():
    print("🔍 --- ASSET AUDIT ---")
    f = os.path.exists("assets/font.ttf")
    t = [f for f in os.listdir('templates') if f.endswith('.mp4')]
    print(f"{'✅' if f else '❌'} Font: assets/font.ttf")
    print(f"{'✅' if t else '❌'} Templates: {len(t)} found")
    return len(t) > 0

async def get_s():
    print("🧠 AI: Generating Script...")
    try:
        with open('config.json', 'r') as f: cfg = json.load(f)
        genai.configure(api_key=K)
        # Use stable model name
        model = genai.GenerativeModel('gemini-1.5-flash')
        p = f"Write a 20s dark psychology script about {random.choice(cfg['topics'])}. Hook, 3 short facts, loop ending. Return ONLY JSON: {{'script': '...', 'caption': '...', 'hashtags': '...'}}"
        r = model.generate_content(p)
        m = re.search(r'\{.*\}', r.text, re.DOTALL)
        return json.loads(m.group()) if m else json.loads(r.text), cfg
    except Exception as e:
        print(f"⚠️ AI Fail: {e}")
        return {"script": "THE MOST DANGEROUS PERSON WATCHES EVERYTHING. THEY ARE CALCULATING YOUR MOVE. THIS IS WHY..."}, {"power_words": ["dangerous"]}

async def get_a(text):
    print("🎙️ AUDIO: Syncing Voice...")
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

def render(data, cfg, vp, dur, ht):
    print("🎬 VIDEO: Rendering Word-by-Word...")
    if ht:
        tm = random.choice([f for f in os.listdir('templates') if f.endswith('.mp4')])
        vi = ["-stream_loop", "-1", "-i", f"templates/{tm}"]
        vb = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,vignette=PI/4"
    else:
        vi = ["-f", "lavfi", "-i", "color=c=0x0a0a0a:s=1080x1920:d=1"]
        vb = "vignette=PI/3"
    
    with open("assets/subs.json", "r") as f: bd = json.load(f)
    ft = "fontfile='assets/font.ttf':" if os.path.exists("assets/font.ttf") else ""
    dfs = []
    for i, item in enumerate(bd):
        s, e, w = item["s"], item["e"], item["w"].upper().replace("'", "")
        c = "yellow" if any(pw.lower() in w.lower() for pw in cfg.get('power_words', [])) else "white"
        if i == 0: c = "red"
        # Word-by-word POP animation
        sz = f"if(lt(t,{s}),0,if(lt(t,{s}+0.05),150,130))"
        # Shadow Layer
        dfs.append(f"drawtext=text='{w}':{ft}fontcolor=black@0.8:fontsize='{sz}+10':x=(w-text_w)/2+5:y=(h-text_h)/2+5:enable='between(t,{s},{e})'")
        # Main Layer
        dfs.append(f"drawtext=text='{w}':{ft}fontcolor={c}:fontsize='{sz}':x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{s},{e})'")

    ai = ["-i", vp]
    mp = "assets/music.mp3"
    if os.path.exists(mp):
        ai += ["-i", mp]
        am = "[1:a]volume=1.5[va];[2:a]volume=0.2[ma];[va][ma]amix=inputs=2:duration=first,loudnorm[aout]"
    else: am = "[1:a]volume=1.5,loudnorm[aout]"

    cmd = ["ffmpeg", "-y"] + vi + ai + ["-filter_complex", f"[0:v]{vb},{','.join(dfs)}[vout];{am}", "-map", "[vout]", "-map", "[aout]", "-t", str(dur), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "output/final.mp4"]
    subprocess.run(cmd)

async def main():
    ht = audit()
    d, cfg = await get_s()
    vp, dur = await get_a(d['script'])
    render(d, cfg, vp, dur, ht)
    if os.path.exists("output/final.mp4"): print("✅ DONE: Video Ready.")

if __name__ == "__main__":
    asyncio.run(main())        # DYNAMIC POP ANIMATION: Grows for first 0.05s then settles
        size = f"if(lt(t,{t_start}),0,if(lt(t,{t_start}+0.05),150,135))"
        
        # Shadow Layer + Main Word
        draw_filters.append(f"drawtext=text='{word}':{f_arg}fontcolor=black@0.8:fontsize='{size}+10':x=(w-text_w)/2+5:y=(h-text_h)/2+5:enable='between(t,{t_start},{t_end})'")
        draw_filters.append(f"drawtext=text='{word}':{f_arg}fontcolor={color}:fontsize='{size}':x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{t_start},{t_end})'")

    filter_complex = f"[0:v]{v_base}"
    if draw_filters: filter_complex += "," + ",".join(draw_filters)
    filter_complex += "[vout]"

    # Audio Mastering
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
