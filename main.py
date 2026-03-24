import os, json, random, asyncio, subprocess, re, requests, time
import google.generativeai as genai
from edge_tts import Communicate

# 🔐 Load Secrets
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
INSTA_TOKEN = os.getenv("INSTA_ACCESS_TOKEN")
INSTA_ID = os.getenv("INSTA_ACCOUNT_ID")

# 📁 Ensure Folders exist
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
        return {
            "script": "The most dangerous person is the one who listens, observes, and says nothing. They already know your next move.",
            "caption": "Silence is power. #psychology",
            "hashtags": "#darkpsychology"
        }

async def create_voice(text):
    path = "assets/voice.mp3"
    comm = Communicate(text, "en-US-GuyNeural", rate="+12%")
    await comm.save(path)
    res = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path], capture_output=True, text=True)
    return path, float(res.stdout or 15.0)

def render_video(data, voice_path, duration):
    # 1. Background Setup
    templates = [f"templates/{f}" for f in os.listdir('templates') if f.endswith('.mp4')]
    if templates:
        video_input = ["-stream_loop", "-1", "-i", f"templates/{random.choice(os.listdir('templates'))}"]
        v_base_filter = "vignette=PI/4,zoompan=z='zoom+0.001':d=125:s=1080x1920"
    else:
        video_input = ["-f", "lavfi", "-i", "color=c=0x0a0a0a:s=1080x1920:d=1"]
        v_base_filter = "noise=alls=5:allf=t+u,vignette=PI/3"

    # 2. Asset Checks
    font = "assets/font.ttf"
    f_arg = f"fontfile='{font}':" if os.path.exists(font) else ""
    m_path, s_path = "assets/music.mp3", "assets/sfx.mp3"
    has_m, has_s = os.path.exists(m_path), os.path.exists(s_path)

    # 3. Subtitles (The POP effect)
    words = re.findall(r"[\w']+", data['script'].upper())
    t_per_w = duration / len(words)
    draw_filters = []
    for i, word in enumerate(words):
        start, end = i * t_per_w, (i + 1) * t_per_w
        color = "yellow" if word.lower() in config['power_words'] else "white"
        if i == 0: color = "red"
        pop = f"120+40*exp(-20*(t-{start}))"
        f = f"drawtext=text='{word}':{f_arg}fontcolor={color}:fontsize='{pop}':borderw=4:bordercolor=black:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{start},{end})'"
        draw_filters.append(f)

    # 4. Audio Inputs & Mixing
    audio_inputs = ["-i", voice_path]
    if has_m: audio_inputs += ["-i", m_path]
    if has_s: audio_inputs += ["-i", s_path]

    # Build Audio Filter
    a_filters = ["[1:a]volume=1.0[va]"] # [va] = voice audio
    mix_labels = ["[va]"]
    
    if has_m:
        a_filters.append("[2:a]volume=0.15[ma]") # [ma] = music audio
        mix_labels.append("[ma]")
    if has_s:
        idx = 2 + int(has_m)
        a_filters.append(f"[{idx}:a]volume=0.8[sa]") # [sa] = sfx audio
        mix_labels.append("[sa]")
    
    if len(mix_labels) > 1:
        a_filter_str = f"{';'.join(a_filters)};{''.join(mix_labels)}amix=inputs={len(mix_labels)}:duration=first[aout]"
    else:
        a_filter_str = f"{a_filters[0].replace('[va]', '[aout]')}"

    # 5. Final FFmpeg Execution (List mode is safer)
    cmd = [
        "ffmpeg", "-y"
    ] + video_input + audio_inputs + [
        "-filter_complex", f"[0:v]{v_base_filter},{','.join(draw_filters)}[vout];{a_filter_str}",
        "-map", "[vout]", "-map", "[aout]",
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "superfast", "-crf", "22",
        "output/final.mp4"
    ]
    
    print("🎬 Rendering...")
    subprocess.run(cmd)

def upload_logic(path, caption):
    if not INSTA_TOKEN or not INSTA_ID or "YOUR" in INSTA_TOKEN:
        print("💡 No API keys found. Download the video from GitHub Artifacts.")
        return
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
