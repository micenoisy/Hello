import os, json, random, asyncio, subprocess, re, requests, time
import google.generativeai as genai
from edge_tts import Communicate

# 1. SETUP & PATHS
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
INSTA_TOKEN = os.getenv("INSTA_ACCESS_TOKEN")
INSTA_ID = os.getenv("INSTA_ACCOUNT_ID")

for f in ['assets', 'templates', 'output']: os.makedirs(f, exist_ok=True)

# 2. BULLETPROOF AI SCRIPT GENERATOR
async def get_script():
    print("🧠 AI: Generating High-Retention Script...")
    try:
        # Load topics from config or use defaults
        with open('config.json', 'r') as f: cfg = json.load(f)
        topic = random.choice(cfg.get('topics', ['manipulation', 'dark psychology']))
        
        genai.configure(api_key=GEMINI_KEY)
        # Use the specific model identifier that works globally
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Act as a Dark Psychology Expert. Write a 25-second script about {topic}.
        Hook: A shocking truth about human behavior.
        Body: 3 punchy, mysterious sentences.
        Loop: End with 'AND THAT IS WHY...' to loop perfectly.
        Return ONLY valid JSON: {{"script": "...", "caption": "...", "hashtags": "..."}}
        """
        
        response = model.generate_content(prompt)
        # Fix: Extract JSON cleanly even if AI adds markdown backticks
        json_str = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        data = json.loads(json_str)
        print(f"✅ AI Success: Topic '{topic}'")
        return data, cfg
    except Exception as e:
        print(f"⚠️ AI FAIL: {e}. Using viral fallback script.")
        fallback = {
            "script": "THE MOST DANGEROUS PERSON IS THE ONE WHO WATCHES EVERYTHING AND SAYS NOTHING. THEY ARE NOT WEAK. THEY ARE CALCULATING EVERY SINGLE MOVE YOU MAKE. AND THAT IS WHY...",
            "caption": "Watch the quiet ones. #psychology",
            "hashtags": "#darkpsychology #mindset"
        }
        # Mock config for fallback
        mock_cfg = {"power_words": ["dangerous", "calculating", "weak", "move"]}
        return fallback, mock_cfg

# 3. MICRO-SYNC AUDIO ENGINE
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
                # Convert 100-nanosecond units to seconds
                word_boundaries.append({
                    "word": chunk["text"],
                    "start": chunk["offset"] / 10**7,
                    "end": (chunk["offset"] + chunk["duration"]) / 10**7
                })

    # Save sync data
    with open("assets/subs.json", "w") as f: json.dump(word_boundaries, f)
    
    # Get total duration
    res = subprocess.run(["ffprobe","-v","0","-show_entries","format=duration","-of","compact=p=0:nk=1",audio_path], capture_output=True, text=True)
    return audio_path, float(res.stdout or 25.0)

# 4. PRO-REELS VIDEO ENGINE
def render_video(data, cfg, voice_path, duration):
    print(f"🎬 VIDEO: Rendering {duration}s Reel...")
    
    # Background Logic
    templates = [f for f in os.listdir('templates') if f.endswith('.mp4')]
    if templates:
        v_in = ["-stream_loop", "-1", "-i", f"templates/{random.choice(templates)}"]
        v_base = "vignette=PI/4,zoompan=z='zoom+0.001':d=125:s=1080x1920"
    else:
        v_in = ["-f", "lavfi", "-i", "color=c=0x0a0a0a:s=1080x1920:d=1"]
        v_base = "noise=alls=10,vignette=PI/3"

    # Subtitle Logic
    with open("assets/subs.json", "r") as f: word_data = json.load(f)
    
    font = "assets/font.ttf"
    f_arg = f"fontfile='{font}':" if os.path.exists(font) else ""
    
    # Build Filter Chain
    draw_filters = []
    # Group words in 2s for better "Instagram Style" pacing
    for i in range(0, len(word_data), 2):
        chunk = word_data[i:i+2]
        t_start = chunk[0]["start"]
        t_end = chunk[-1]["end"]
        phrase = " ".join([w["word"] for w in chunk]).upper().replace("'", "").replace(":", "")
        
        # Power word highlighting
        color = "yellow" if any(pw.lower() in phrase.lower() for pw in cfg.get('power_words', [])) else "white"
        
        # The 'Pop' animation
        size = f"if(lt(t,{t_start}),0,if(lt(t,{t_start}+0.1),120+45*(t-{t_start})/0.1,120))"
        
        # Layer 1: Shadow Glow
        draw_filters.append(f"drawtext=text='{phrase}':{f_arg}fontcolor=black@0.8:fontsize='{size}+10':x=(w-text_w)/2+4:y=(h-text_h)/2+4:enable='between(t,{t_start},{t_end})'")
        # Layer 2: Main Text
        draw_filters.append(f"drawtext=text='{phrase}':{f_arg}fontcolor={color}:fontsize='{size}':x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{t_start},{t_end})'")

    # Filter Assembly
    filter_complex = f"[0:v]{v_base}"
    if draw_filters:
        filter_complex += "," + ",".join(draw_filters)
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
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ FFMPEG ERROR: {result.stderr}")

# 5. EXECUTE
async def main():
    start_time = time.time()
    print("🚀 AGENT STARTING...")
    
    # Step 1: Script
    data, cfg = await get_script()
    
    # Step 2: Sync Audio
    voice_file, duration = await get_audio(data['script'])
    
    # Step 3: Render
    render_video(data, cfg, voice_file, duration)
    
    if os.path.exists("output/final.mp4"):
        print(f"✅ SUCCESS: Video generated in {round(time.time()-start_time, 2)}s")
    else:
        print("❌ FAILED: Video not found in output folder.")

if __name__ == "__main__":
    asyncio.run(main())
