import os, json, random, asyncio, subprocess, re, requests, time
import google.generativeai as genai
from edge_tts import Communicate

# 🔐 SECRETS
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
INSTA_TOKEN = os.getenv("INSTA_ACCESS_TOKEN")
INSTA_ID = os.getenv("INSTA_ACCOUNT_ID")

for f in ['assets', 'templates', 'output']: os.makedirs(f, exist_ok=True)

# 1. ASSET AUDITOR (Checks everything before starting)
def audit_assets():
    print("\n🔍 --- ASSET AUDIT REPORT ---")
    f_exists = os.path.exists("assets/font.ttf")
    m_exists = os.path.exists("assets/music.mp3")
    t_count = len([f for f in os.listdir('templates') if f.endswith('.mp4')])
    
    print(f"{'✅' if f_exists else '❌'} FONT: assets/font.ttf")
    print(f"{'✅' if m_exists else '❌'} MUSIC: assets/music.mp3")
    print(f"{'✅' if t_count > 0 else '❌'} TEMPLATES: {t_count} found")
    print("----------------------------\n")
    return t_count > 0

# 2. POWERFUL AI SCRIPT GENERATOR (Fixed 404 Error)
async def generate_script():
    print("🧠 AI: Generating unique Dark Psychology script...")
    try:
        with open('config.json', 'r') as f: cfg = json.load(f)
        genai.configure(api_key=GEMINI_KEY)
        
        # FIXED: Using the latest stable model identifier
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        topic = random.choice(cfg['topics'])
        prompt = f"""
        Act as a Master of Dark Psychology. Write a 20-second viral Instagram Reel script about {topic}.
        - Start with a massive hook (e.g., 'THE REASON THEY...', 'STOP BEING...').
        - Use short, aggressive sentences (3-5 words max).
        - No emojis. No hashtags in the script.
        - Topic must be mysterious and slightly dangerous.
        Return ONLY valid JSON: {{"script": "...", "caption": "...", "hashtags": "..."}}
        """
        
        response = model.generate_content(prompt)
        json_str = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        return json.loads(json_str), cfg
    except Exception as e:
        print(f"⚠️ AI FAIL ({e}): Using Fallback.")
        return {
            "script": "THE MOST DANGEROUS PERSON IS THE ONE WHO WATCHES EVERYTHING AND SAYS NOTHING. THEY ARE CALCULATING YOUR EVERY MOVE. AND THAT IS WHY...",
            "caption": "Silence is power.",
            "hashtags": "#darkpsychology"
        }, {"power_words": ["dangerous", "calculating", "nothing"]}

# 3. WORD-BY-WORD AUDIO SYNC ENGINE
async def generate_audio(text):
    print("🎙️ AUDIO: Generating micro-synced voiceover...")
    voice = "en-US-ChristopherNeural"
    communicate = Communicate(text, voice, rate="+15%", pitch="-5Hz")
    
    word_boundaries = []
    audio_path = "assets/voice.mp3"
    
    with open(audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # Micro-sync timestamp collection
                word_boundaries.append({
                    "word": chunk["text"],
                    "start": chunk["offset"] / 10**7,
                    "end": (chunk["offset"] + chunk["duration"]) / 10**7
                })

    with open("assets/subs.json", "w") as f: json.dump(word_boundaries, f)
    res = subprocess.run(["ffprobe","-v","0","-show_entries","format=duration","-of","compact=p=0:nk=1",audio_path], capture_output=True, text=True)
    return audio_path, float(res.stdout or 15.0)

# 4. WORD-BY-WORD DYNAMIC RENDER (NO ZOOM)
def render_video(data, cfg, voice_path, duration, has_template):
    print(f"🎬 VIDEO: Rendering {duration}s Word-by-Word Reel...")
    
    if has_template:
        t_file = random.choice([f for f in os.listdir('templates') if f.endswith('.mp4')])
        v_in = ["-stream_loop", "-1", "-i", f"templates/{t_file}"]
        v_base = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,vignette=PI/4"
    else:
        v_in = ["-f", "lavfi", "-i", "color=c=0x0a0a0a:s=1080x1920:d=1"]
        v_base = "vignette=PI/3"

    with open("assets/subs.json", "r") as f: word_data = json.load(f)
    font = "assets/font.ttf"
    f_arg = f"fontfile='{font}':" if os.path.exists(font) else ""
    
    draw_filters = []
    for item in word_data:
        t_start = item["start"]
        t_end = item["end"]
        word = item["word"].upper().replace("'", "").replace(":", "")
        
        # Color trigger
        color = "yellow" if any(pw.lower() in word.lower() for pw in cfg.get('power_words', [])) else "white"
        if word == word_data[0]["word"].upper(): color = "red" # First word Red

        # DYNAMIC POP ANIMATION: Grows for first 0.05s then settles
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
