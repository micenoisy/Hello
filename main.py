import os, json, random, asyncio, subprocess, re, requests, time
import google.generativeai as genai
from edge_tts import Communicate

# 1. SECRETS & PATHS
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
INSTA_TOKEN = os.getenv("INSTA_ACCESS_TOKEN")
INSTA_ID = os.getenv("INSTA_ACCOUNT_ID")

for f in ['assets', 'templates', 'output']: os.makedirs(f, exist_ok=True)

# 2. ASSET AUDITOR (Error Handling for Files)
def audit_assets():
    print("\n🔍 --- ASSET AUDIT REPORT ---")
    font_exists = os.path.exists("assets/font.ttf")
    music_exists = os.path.exists("assets/music.mp3")
    templates = [f for f in os.listdir('templates') if f.endswith('.mp4')]
    
    print(f"{'✅' if font_exists else '❌'} FONT: {'font.ttf found' if font_exists else 'MISSING (Subtitles will look bad)'}")
    print(f"{'✅' if music_exists else '❌'} MUSIC: {'music.mp3 found' if music_exists else 'MISSING (Video will be silent)'}")
    print(f"{'✅' if templates else '❌'} TEMPLATES: {len(templates)} videos found.")
    
    if not font_exists: print("⚠️ WARNING: Upload a bold font to assets/font.ttf for viral subtitles.")
    print("----------------------------\n")
    return templates

# 3. POWERFUL SCRIPT GENERATOR
async def get_script():
    print("🧠 AI: Generating Powerful Dark Psychology Script...")
    try:
        with open('config.json', 'r') as f: cfg = json.load(f)
        genai.configure(api_key=GEMINI_KEY)
        
        # FIXED: Model string updated for stability
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = """
        Write a 20-second viral script about a dark psychology tactic.
        - Start with a powerful hook.
        - Use aggressive, mysterious, short sentences.
        - End with a loop-ready cliffhanger.
        - NO EMOJIS. NO HASHTAGS in the script.
        Return ONLY valid JSON: {"script": "...", "caption": "...", "hashtags": "..."}
        """
        
        response = model.generate_content(prompt)
        json_str = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        return json.loads(json_str), cfg
    except Exception as e:
        print(f"⚠️ AI FAIL: {e}. Using viral fallback.")
        return {
            "script": "THE MOST DANGEROUS PERSON IS THE ONE WHO WATCHES EVERYTHING AND SAYS NOTHING. THEY ARE NOT WEAK. THEY ARE CALCULATING. AND THAT IS WHY...",
            "caption": "Silence is the ultimate weapon.",
            "hashtags": "#darkpsychology #mindset"
        }, {"power_words": ["dangerous", "calculating", "weak"]}

# 4. MICRO-SYNC AUDIO ENGINE
async def get_audio(text):
    print("🎙️ AUDIO: Generating micro-synced voiceover...")
    voice = "en-US-ChristopherNeural"
    communicate = Communicate(text, voice, rate="+10%", pitch="-5Hz")
    
    word_boundaries = []
    audio_path = "assets/voice.mp3"
    
    with open(audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_boundaries.append({
                    "word": chunk["text"],
                    "start": chunk["offset"] / 10**7,
                    "end": (chunk["offset"] + chunk["duration"]) / 10**7
                })

    with open("assets/subs.json", "w") as f: json.dump(word_boundaries, f)
    res = subprocess.run(["ffprobe","-v","0","-show_entries","format=duration","-of","compact=p=0:nk=1",audio_path], capture_output=True, text=True)
    return audio_path, float(res.stdout or 20.0)

# 5. DYNAMIC SUBTITLE & VIDEO RENDER (NO ZOOM)
def render_video(data, cfg, voice_path, duration, templates):
    print(f"🎬 VIDEO: Rendering {duration}s Reel...")
    
    # Select Template
    if templates:
        v_in = ["-stream_loop", "-1", "-i", f"templates/{random.choice(templates)}"]
        v_base = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,vignette=PI/4"
    else:
        v_in = ["-f", "lavfi", "-i", "color=c=0x0a0a0a:s=1080x1920:d=1"]
        v_base = "vignette=PI/3"

    # Load Subs
    with open("assets/subs.json", "r") as f: word_data = json.load(f)
    font = "assets/font.ttf"
    f_arg = f"fontfile='{font}':" if os.path.exists(font) else ""
    
    draw_filters = []
    # Group into 1-2 words for "Viral Pacing"
    for i in range(0, len(word_data), 2):
        chunk = word_data[i:i+2]
        t_start = chunk[0]["start"]
        t_end = chunk[-1]["end"]
        phrase = " ".join([w["word"] for w in chunk]).upper().replace("'", "").replace(":", "")
        
        color = "yellow" if any(pw.lower() in phrase.lower() for pw in cfg.get('power_words', [])) else "white"
        
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
