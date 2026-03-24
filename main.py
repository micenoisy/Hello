import os, json, random, asyncio, subprocess, re, requests, time
import google.generativeai as genai
from edge_tts import Communicate

# 🔐 SECRETS
K, T, I = os.getenv("GEMINI_API_KEY"), os.getenv("INSTA_ACCESS_TOKEN"), os.getenv("INSTA_ACCOUNT_ID")
for folder in ['assets', 'templates', 'output']: os.makedirs(folder, exist_ok=True)

def check_system():
    print("🎬 --- SYSTEM INITIALIZING ---")
    if not K: print("❌ ERROR: GEMINI_API_KEY missing!"); return False
    if not os.path.exists("assets/font.ttf"): print("⚠️ WARNING: No assets/font.ttf found.")
    return True

# 🧠 POWERFUL SCRIPT GENERATOR
async def generate_viral_script():
    try:
        topic = random.choice(cfg['topics'])
        genai.configure(api_key=K)
        # FIXED: Using stable model string
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"Act as a Dark Psychology Master. Write a 25s viral script about {topic}. Start with a massive hook. NO EMOJIS. Return ONLY JSON: {{'script': '...', 'caption': '...', 'hashtags': '...'}}"
        
        response = model.generate_content(prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"✅ AI Script Generated: {topic}")
        return data
    except Exception as e:
        print(f"❌ AI ERROR: {str(e)}")
        return {"script": "THE QUIETEST PERSON IN THE ROOM IS OFTEN THE MOST DANGEROUS. THEY ARE NOT WEAK. THEY ARE CALCULATING. WATCH THEM. THIS IS WHY...", "caption": "Silence is power.", "hashtags": "#darkpsychology"}

# 🎙️ MICRO-SYNC VOICE GENERATION
async def generate_synced_audio(text):
    voice = "en-US-ChristopherNeural"
    communicate = Communicate(text, voice, rate="+10%", pitch="-5Hz")
    
    word_data = []
    # Manually collect word timings for 100% precision
    with open("assets/voice.mp3", "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # Convert 100ns units to seconds
                word_data.append({
                    "word": chunk["text"],
                    "start": chunk["offset"] / 10**7,
                    "end": (chunk["offset"] + chunk["duration"]) / 10**7
                })

    with open("assets/subs.json", "w") as f:
        json.dump(word_data, f)
    
    res = subprocess.run(["ffprobe","-v","0","-show_entries","format=duration","-of","compact=p=0:nk=1","assets/voice.mp3"], capture_output=True, text=True)
    return float(res.stdout or 25.0)

# 🎬 DYNAMIC RENDER
def render_viral_video(data, duration):
    ts = [f for f in os.listdir('templates') if f.endswith('.mp4')]
    v_in = ["-stream_loop","-1","-i", f"templates/{random.choice(ts)}"] if ts else ["-f","lavfi","-i","color=c=0x0a0a0a:s=1080x1920:d=1"]
    v_filt = "vignette=PI/4,zoompan=z='zoom+0.001':d=125:s=1080x1920" if ts else "noise=alls=10,vignette=PI/3"

    with open("assets/subs.json", "r") as f:
        word_subs = json.load(f)

    f_arg = "fontfile='assets/font.ttf':" if os.path.exists("assets/font.ttf") else ""
    draw_filters = []
    
    # Phrase grouping: shows 2 words at a time for better visual sync
    for i in range(0, len(word_subs), 2):
        chunk = word_subs[i:i+2]
        start_t = chunk[0]["start"]
        end_t = chunk[-1]["end"]
        phrase = " ".join([w["word"] for w in chunk]).upper().replace("'", "")
        
        color = "yellow" if any(pw.lower() in phrase.lower() for pw in cfg['power_words']) else "white"
        
        # Smooth Pop & Shake Animation
        size = f"if(lt(t,{start_t}),0,if(lt(t,{start_t}+0.1),120+40*(t-{start_t})/0.1,120))"
        
        # Draw Black Shadow then Colored Text
        draw_filters.append(f"drawtext=text='{phrase}':{f_arg}fontcolor=black@0.7:fontsize='{size}+8':x=(w-text_w)/2+4:y=(h-text_h)/2+4:enable='between(t,{start_t},{end_t})'")
        draw_filters.append(f"drawtext=text='{phrase}':{f_arg}fontcolor={color}:fontsize='{size}':x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{start_t},{end_t})'")

    m_path = "assets/music.mp3"
    ai = ["-i", "assets/voice.mp3"]
    if os.path.exists(m_path): ai += ["-i", m_path]
    
    a_mix = "[1:a]volume=1.5[va]"
    labels = ["[va]"]
    if os.path.exists(m_path):
        a_mix += ";[2:a]volume=0.2[ma]"
        labels.append("[ma]")
    
    final_a = f"{a_mix};{''.join(labels)}amix=inputs={len(labels)}:duration=first,loudnorm[aout]" if len(labels)>1 else "[1:a]volume=1.5[aout]"

    cmd = ["ffmpeg","-y"] + v_in + ai + [
        "-filter_complex", f"[0:v]{v_filt},{','.join(draw_filters)}[vout];{final_a}",
        "-map", "[vout]", "-map", "[aout]", "-t", str(duration),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "output/final.mp4"
    ]
    subprocess.run(cmd)

async def main():
    if not check_system(): return
    with open('config.json', 'r') as f: globals()['cfg'] = json.load(f)
    
    data = await generate_viral_script()
    duration = await generate_synced_audio(data['script'])
    
    print(f"🎬 Rendering Video...")
    render_viral_video(data, duration)
    
    if os.path.exists("output/final.mp4"):
        print("✅ SUCCESS: Perfectly Synced Video Generated.")

if __name__ == "__main__":
    asyncio.run(main())
