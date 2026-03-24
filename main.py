import os, json, random, asyncio, subprocess, re, requests, time
import google.generativeai as genai
from edge_tts import Communicate

# 🔐 Load Secrets
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
INSTA_TOKEN = os.getenv("INSTA_ACCESS_TOKEN")
INSTA_ID = os.getenv("INSTA_ACCOUNT_ID")

for folder in ['assets', 'templates', 'output']:
    os.makedirs(folder, exist_ok=True)

with open('config.json', 'r') as f:
    config = json.load(f)

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

async def generate_content():
    topic = random.choice(config['topics'])
    prompt = f"Create a 15s dark psychology script about {topic}. Return JSON: {{'script': '...', 'caption': '...', 'hashtags': '...'}}. Hook must be strong. US English."
    try:
        response = model.generate_content(prompt)
        return json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
    except:
        return {"script": "The strongest people are usually the ones who stay silent.", "caption": "Silence is power.", "hashtags": "#darkpsychology"}

async def create_voice(text):
    path = "assets/voice.mp3"
    comm = Communicate(text, "en-US-GuyNeural", rate="+12%")
    await comm.save(path)
    res = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path], capture_output=True, text=True)
    return path, float(res.stdout or 15.0)

def render_video(data, voice_path, duration):
    # 1. Background
    templates = [f for f in os.listdir('templates') if f.endswith('.mp4')]
    if templates:
        v_in = ["-stream_loop", "-1", "-i", f"templates/{random.choice(templates)}"]
        v_filt = "vignette=PI/4,zoompan=z='zoom+0.001':d=125:s=1080x1920"
    else:
        v_in = ["-f", "lavfi", "-i", "color=c=0x0a0a0a:s=1080x1920:d=1"]
        v_filt = "vignette=PI/3"

    # 2. Assets
    font = "assets/font.ttf"
    f_path = f"fontfile='{font}':" if os.path.exists(font) else ""
    m_path, s_path = "assets/music.mp3", "assets/sfx.mp3"
    
    # 3. Subtitles (FIXED MATH)
    words = re.findall(r"[\w']+", data['script'].upper())
    t_per_w = duration / len(words)
    draw_filters = []
    for i, word in enumerate(words):
        start = i * t_per_w
        end = (i + 1) * t_per_w
        color = "yellow" if word.lower() in config['power_words'] else "white"
        if i == 0: color = "red"
        
        # Fixed formula to prevent "fontsize overflow"
        # We use max(0, t-start) so the exponent never goes positive/huge
        size = f"if(lt(t,{start}),0,100+40*exp(-15*(t-{start})))"
        
        # Clean text for FFmpeg
        clean_word = word.replace("'", "").replace(":", "")
        f = f"drawtext=text='{clean_word}':{f_path}fontcolor={color}:fontsize='{size}':borderw=4:bordercolor=black:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{start},{end})'"
        draw_filters.append(f)

    # 4. Audio Mixing
    a_ins = ["-i", voice_path]
    has_m = os.path.exists(m_path)
    has_s = os.path.exists(s_path)
    if has_m: a_ins += ["-i", m_path]
    if has_s: a_ins += ["-i", s_path]

    a_mix = "[1:a]volume=1.0[va]"
    labels = ["[va]"]
    if has_m:
        a_mix += ";[2:a]volume=0.15[ma]"
        labels.append("[ma]")
    if has_s:
        idx = 2 + int(has_m)
        a_mix += f";[{idx}:a]volume=0.8[sa]"
        labels.append("[sa]")
    
    if len(labels) > 1:
        final_a = f"{a_mix};{''.join(labels)}amix=inputs={len(labels)}:duration=first[aout]"
    else:
        final_a = "[1:a]volume=1.0[aout]"

    # 5. Execute
    cmd = ["ffmpeg", "-y"] + v_in + a_ins + [
        "-filter_complex", f"[0:v]{v_filt},{','.join(draw_filters)}[vout];{final_a}",
        "-map", "[vout]", "-map", "[aout]", "-t", str(duration),
        "-c:v", "libx264", "-preset", "superfast", "-crf", "22", "output/final.mp4"
    ]
    
    print("🎬 Rendering...")
    subprocess.run(cmd)

async def main():
    print("🚀 Agent Starting...")
    data = await generate_content()
    v_path, duration = await create_voice(data['script'])
    render_video(data, v_path, duration)
    
    if os.path.exists("output/final.mp4"):
        print("✅ Success! Video ready in output/final.mp4")
    else:
        print("❌ Video creation failed.")

if __name__ == "__main__":
    asyncio.run(main())        return
    try:
        files = {'fileToUpload': open(path, 'rb')}
        v_url = requests.post("https://catbox.moe/user/api.php", data={'reqtype': 'fileupload'}, files=files).text
        r = requests.post(f"https://graph.facebook.com/v19.0/{INSTA_ID}/media", data={
            'video_url': v_url, 'caption': caption, 'media_type': 'REELS', 'access_token': INSTA_TOKEN
        }).json()
        cid = r.get('id')
        if cid:
            print("⏳ Processing upload...")
            time.sleep(45)
            requests.post(f"https://graph.facebook.com/v19.0/{INSTA_ID}/media_publish", data={'creation_id': cid, 'access_token': INSTA_TOKEN})
            print("🚀 Posted!")
    except Exception as e:
        print(f"❌ Upload failed: {e}")

async def main():
    print("🚀 Agent Starting...")
    data = await generate_content()
    voice_path, duration = await create_voice(data['script'])
    render_video(data, voice_path, duration)
    
    if os.path.exists("output/final.mp4"):
        print("✅ Video Created Successfully.")
        upload_logic("output/final.mp4", f"{data['caption']}\n\n{data['hashtags']}")
    else:
        print("❌ Video creation failed.")

if __name__ == "__main__":
    asyncio.run(main())
