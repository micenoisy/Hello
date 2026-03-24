import os, json, random, asyncio, subprocess, re, requests, time
import google.generativeai as genai
from edge_tts import Communicate, SubMaker

# 1. 🔐 SECRETS & SYSTEM CHECK
K, T, I = os.getenv("GEMINI_API_KEY"), os.getenv("INSTA_ACCESS_TOKEN"), os.getenv("INSTA_ACCOUNT_ID")
for folder in ['assets', 'templates', 'output']: os.makedirs(folder, exist_ok=True)

def check_system():
    print("🎬 --- SYSTEM INITIALIZING ---")
    if not K: print("❌ ERROR: GEMINI_API_KEY is missing in Secrets!"); return False
    # Check for Font (Crucial for Instagram)
    if not os.path.exists("assets/font.ttf"):
        print("⚠️ WARNING: No assets/font.ttf found. Subtitles will look basic.")
    return True

# 2. 🧠 POWERFUL SCRIPT GENERATOR (With Error Handling)
async def generate_viral_script():
    try:
        topic = random.choice(cfg['topics'])
        genai.configure(api_key=K)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Act as a Dark Psychology Master. Write a 25-second viral script about {topic}.
        - Hook (0-3s): Start with 'THE REASON THEY...' or 'NEVER TRUST...'
        - Deep Insight (3-20s): Explain a manipulation tactic or human weakness.
        - The Loop (20-25s): End with a cliffhanger that leads back to the hook.
        - Rules: Use short, aggressive sentences. NO EMOJIS.
        Return ONLY JSON: {{"script": "...", "caption": "...", "hashtags": "..."}}
        """
        
        response = model.generate_content(prompt)
        # Check if response was blocked or empty
        if not response.text: raise ValueError("AI returned empty content")
        
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"✅ AI Script Generated for Topic: {topic}")
        return data

    except Exception as e:
        print(f"❌ AI ERROR: {str(e)}")
        print("💡 FALLBACK: Using pre-stored high-performance script.")
        return {
            "script": "THE MOST DANGEROUS PERSON IS THE ONE WHO LISTENS, OBSERVES, AND SAYS NOTHING. THEY ARE CALCULATING YOUR EVERY MOVE. THIS IS WHY...",
            "caption": "Silence is the ultimate weapon.",
            "hashtags": "#darkpsychology #manipulation #mindset"
        }

# 3. 🎙️ MICRO-SYNC VOICE GENERATION
async def generate_synced_audio(text):
    # Using 'Brian' or 'Christopher' for high-authority USA male voice
    voice = "en-US-ChristopherNeural"
    communicate = Communicate(text, voice, rate="+10%", pitch="-5Hz")
    submaker = SubMaker()
    
    with open("assets/voice.mp3", "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.create_sub((chunk["start"], chunk["duration"]), chunk["text"])

    # This creates a perfect word-by-word timestamp list
    with open("assets/subs.json", "w") as f:
        json.dump(submaker.subs, f)
    
    duration = subprocess.run(["ffprobe","-v","0","-show_entries","format=duration","-of","compact=p=0:nk=1","assets/voice.mp3"], capture_output=True, text=True).stdout
    return float(duration or 25.0)

# 4. 🎬 DYNAMIC FFmpeg RENDERING (Stacked & Pop)
def render_viral_video(data, duration):
    ts = [f for f in os.listdir('templates') if f.endswith('.mp4')]
    if ts:
        v_in = ["-stream_loop","-1","-i", f"templates/{random.choice(ts)}"]
        v_filt = "vignette=PI/4,zoompan=z='zoom+0.001':d=125:s=1080x1920"
    else:
        v_in = ["-f","lavfi","-i","color=c=0x0a0a0a:s=1080x1920:d=1"]
        v_filt = "noise=alls=10:allf=t+u,vignette=PI/3"

    with open("assets/subs.json", "r") as f:
        word_subs = json.load(f)

    font_path = "assets/font.ttf"
    f_arg = f"fontfile='{font_path}':" if os.path.exists(font_path) else ""
    
    draw_filters = []
    for sub in word_subs:
        start_time = sub[0][0] / 10**7 # Convert microseconds to seconds
        end_time = (sub[0][0] + sub[0][1]) / 10**7
        word = sub[1].upper().replace("'", "").replace(":", "")
        
        # Style: Power words Yellow, Others White
        color = "yellow" if word.lower() in cfg['power_words'] else "white"
        
        # THE POP ANIMATION: Grows for first 0.1s then stays
        pop_size = f"if(lt(t,{start_time}),0,if(lt(t,{start_time}+0.1),120+60*(t-{start_time})/0.1,120))"
        
        # Filter 1: Shadow Glow
        draw_filters.append(f"drawtext=text='{word}':{f_arg}fontcolor=black@0.6:fontsize='{pop_size}+10':x=(w-text_w)/2+5:y=(h-text_h)/2+5:enable='between(t,{start_time},{end_time})'")
        # Filter 2: Main Text
        draw_filters.append(f"drawtext=text='{word}':{f_arg}fontcolor={color}:fontsize='{pop_size}':x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{start_time},{end_time})'")

    # Audio Assets (Music + SFX)
    m_path, s_path = "assets/music.mp3", "assets/sfx.mp3"
    ai = ["-i", "assets/voice.mp3"]
    if os.path.exists(m_path): ai += ["-i", m_path]
    if os.path.exists(s_path): ai += ["-i", s_path]
    
    # Audio Mix Logic
    a_mix = "[1:a]volume=1.4[va]"
    labels = ["[va]"]
    if os.path.exists(m_path): a_mix += ";[2:a]volume=0.2[ma]"; labels.append("[ma]")
    if os.path.exists(s_path): idx = 2 + int(os.path.exists(m_path)); a_mix += f";[{idx}:a]volume=0.8[sa]"; labels.append("[sa]")
    
    fa_str = f"{a_mix};{''.join(labels)}amix=inputs={len(labels)}:duration=first,loudnorm[aout]" if len(labels)>1 else "[1:a]volume=1.4[aout]"

    # Final Command
    cmd = ["ffmpeg","-y"] + v_in + ai + [
        "-filter_complex", f"[0:v]{v_filt},{','.join(draw_filters)}[vout];{fa_str}",
        "-map", "[vout]", "-map", "[aout]", "-t", str(duration),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "output/final.mp4"
    ]
    subprocess.run(cmd)

async def main():
    if not check_system(): return
    with open('config.json', 'r') as f: globals()['cfg'] = json.load(f)
    
    print("🧠 Fetching AI Script...")
    data = await generate_viral_script()
    
    print("🎙️ Generating Perfectly Synced Voiceover...")
    duration = await generate_synced_audio(data['script'])
    
    print(f"🎬 Rendering {round(duration,1)}s Video...")
    render_viral_video(data, duration)
    
    if os.path.exists("output/final.mp4"):
        print("🚀 SUCCESS: Video Sync at 100% precision.")

if __name__ == "__main__":
    asyncio.run(main())
