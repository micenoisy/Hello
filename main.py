import os, json, random, asyncio, subprocess, re, requests, time
import google.generativeai as genai
from edge_tts import Communicate

# 1. SETUP & SYSTEM AUDITOR
K, T, I = os.getenv("GEMINI_API_KEY"), os.getenv("INSTA_ACCESS_TOKEN"), os.getenv("INSTA_ACCOUNT_ID")
for folder in ['assets', 'templates', 'output']: os.makedirs(folder, exist_ok=True)

def audit_system():
    print("🔍 --- SYSTEM HEALTH CHECK ---")
    checks = {
        "Font": "assets/font.ttf",
        "Music": "assets/music.mp3",
        "SFX": "assets/sfx.mp3",
        "Templates": "templates/"
    }
    for name, path in checks.items():
        if name == "Templates":
            count = len([f for f in os.listdir(path) if f.endswith('.mp4')])
            print(f"{'✅' if count > 0 else '❌'} {name}: {count} videos found.")
        else:
            print(f"{'✅' if os.path.exists(path) else '❌'} {name}: {'Found' if os.path.exists(path) else 'MISSING'}")
    print("------------------------------\n")

with open('config.json', 'r') as f: cfg = json.load(f)
genai.configure(api_key=K)
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. VIRAL SCRIPT GENERATION (20-25 Seconds)
async def get_script():
    topic = random.choice(cfg['topics'])
    prompt = f"""
    Create a 25-second dark psychology script about {topic}. 
    Structure:
    1. Hook: A 'Red Pill' shock statement.
    2. Body: 3 deep, mysterious psychological facts.
    3. Loop: End the script with 'THIS IS WHY...' so it loops back to the start.
    Return JSON: {{'script': '...', 'caption': '...', 'hashtags': '...'}}
    """
    try:
        r = model.generate_content(prompt)
        m = re.search(r'\{.*\}', r.text, re.DOTALL)
        return json.loads(m.group())
    except:
        return {"script": "THE MOST DANGEROUS PERSON IS THE ONE WHO WATCHES EVERYTHING AND SAYS NOTHING. THEY ARE NOT WEAK. THEY ARE CALCULATING EVERY SINGLE MOVE YOU MAKE. THIS IS WHY...", "caption": "Watch the quiet ones.", "hashtags": "#psychology"}

# 3. VOICE GENERATION (Deep & Authoritative)
async def get_voice(text):
    p = "assets/voice.mp3"
    # Using 'Christopher' for a deeper, more 'Documentary/Dark' feel
    comm = Communicate(text, "en-US-ChristopherNeural", rate="+5%", pitch="-10Hz")
    await comm.save(p)
    d = subprocess.run(["ffprobe","-v","0","-show_entries","format=duration","-of","compact=p=0:nk=1",p], capture_output=True, text=True).stdout
    return p, float(d or 20.0)

# 4. DYNAMIC VIDEO RENDERING
def render_video(data, vp, dur):
    # Background Logic
    ts = [f for f in os.listdir('templates') if f.endswith('.mp4')]
    if ts:
        vi = ["-stream_loop","-1","-i",f"templates/{random.choice(ts)}"]
        vf = "vignette=PI/4,zoompan=z='zoom+0.001':d=125:s=1080x1920"
    else:
        # Generate a high-quality "Dark Moving Space" if no templates
        vi = ["-f","lavfi","-i","cellauto=s=1080x1920:rate=10"]
        vf = "hue=s=0,vignette=PI/3,curve=preset=darker"

    font = "assets/font.ttf"
    f_arg = f"fontfile='{font}':" if os.path.exists(font) else ""
    
    # Phrase-Based Sync (Groups of 2 words for better readability)
    words = re.findall(r"[\w']+", data['script'].upper())
    phrases = [" ".join(words[i:i+2]) for i in range(0, len(words), 2)]
    t_per_p = dur / len(phrases)
    
    draw_filters = []
    for i, p in enumerate(phrases):
        s, e = i*t_per_p, (i+1)*t_per_p
        color = "yellow" if any(pw.upper() in p for pw in cfg['power_words']) else "white"
        # Dynamic "Pop" size: starts big, settles down
        size = f"if(lt(t,{s}),0,140+60*exp(-10*(t-{s})))"
        clean_p = p.replace("'","").replace(":","")
        
        # Glow Effect (Layered Text)
        draw_filters.append(f"drawtext=text='{clean_p}':{f_arg}fontcolor=black@0.5:fontsize='{size}':borderw=10:bordercolor=black:x=(w-text_w)/2:y=(h-text_h)/2+5:enable='between(t,{s},{e})'")
        draw_filters.append(f"drawtext=text='{clean_p}':{f_arg}fontcolor={color}:fontsize='{size}':x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{s},{e})'")

    # Audio Layering
    ai = ["-i", vp]
    mp, sp = "assets/music.mp3", "assets/sfx.mp3"
    hm, hs = os.path.exists(mp), os.path.exists(sp)
    if hm: ai += ["-i", mp]
    if hs: ai += ["-i", sp]
    
    am = "[1:a]volume=1.5[va]" # Boost voice
    ls = ["[va]"]
    if hm: am += ";[2:a]volume=0.2[ma]"; ls.append("[ma]")
    if hs: idx = 2+int(hm); am += f";[{idx}:a]volume=0.5[sa]"; ls.append("[sa]")
    
    fa_str = f"{am};{''.join(ls)}amix=inputs={len(ls)}:duration=first[aout]" if len(ls)>1 else "[1:a]volume=1.0[aout]"

    cmd = ["ffmpeg","-y"] + vi + ai + [
        "-filter_complex", f"[0:v]{vf},{','.join(draw_filters)}[vout];{fa_str}",
        "-map", "[vout]", "-map", "[aout]", "-t", str(dur),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "output/final.mp4"
    ]
    subprocess.run(cmd)

async def main():
    audit_system()
    print("🔥 STEP 1: Scripting...")
    d = await get_script()
    print(f"🎙️ STEP 2: Voiceover ({len(d['script'])} chars)...")
    vp, dur = await get_voice(d['script'])
    print(f"🎬 STEP 3: Rendering {dur}s video...")
    render_video(d, vp, dur)
    if os.path.exists("output/final.mp4"):
        print(f"✅ DONE: final.mp4 generated ({round(dur, 2)}s)")
        # Add your upload_to_insta logic here if keys are ready

if __name__ == "__main__":
    asyncio.run(main())
