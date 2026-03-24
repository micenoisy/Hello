import os, json, random, asyncio, subprocess, re, requests, time
import google.generativeai as genai
from edge_tts import Communicate

# 🔐 Load Secrets
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
INSTA_TOKEN = os.getenv("INSTA_ACCESS_TOKEN")
INSTA_ID = os.getenv("INSTA_ACCOUNT_ID")

# 📁 Ensure Folders Exist
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
            "caption": "Silence is power.",
            "hashtags": "#psychology #dark"
        }

async def create_voice(text):
    path = "assets/voice.mp3"
    comm = Communicate(text, "en-US-GuyNeural", rate="+12%")
    await comm.save(path)
    res = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path], capture_output=True, text=True)
    return path, float(res.stdout or 15.0)

def render_video(data, voice_path, duration):
    # 1. Check for Template
    templates = [f"templates/{f}" for f in os.listdir('templates') if f.endswith('.mp4')]
    if templates:
        video_input = f"-stream_loop -1 -i {random.choice(templates)}"
        video_filter = "vignette=PI/4,zoompan=z='zoom+0.001':d=125:s=1080x1920"
    else:
        # FALLBACK: Dark Gradient Background if no templates exist
        video_input = "-f lavfi -i color=c=0x1a1a1a:s=1080x1920:d=1"
        video_filter = "noise=alls=10:allf=t+u,vignette=PI/3"

    # 2. Check for Font
    font_path = "assets/font.ttf"
    font_arg = f"fontfile='{font_path}':" if os.path.exists(font_path) else ""

    # 3. Check for Audio Assets
    music_path = "assets/music.mp3"
    sfx_path = "assets/sfx.mp3"
    has_music = os.path.exists(music_path)
    has_sfx = os.path.exists(sfx_path)

    # 4. Build Subtitles
    words = re.findall(r"[\w']+", data['script'].upper())
    t_per_w = duration / len(words)
    draw_filters = []
    for i, word in enumerate(words):
        start, end = i * t_per_w, (i + 1) * t_per_w
        color = "yellow" if word.lower() in config['power_words'] else "white"
        pop = f"115+35*exp(-25*(t-{start}))"
        f = f"drawtext=text='{word}':{font_arg}fontcolor={color}:fontsize='{pop}':borderw=4:bordercolor=black:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{start},{end})'"
        draw_filters.append(f)

    # 5. Build Final Command
    audio_inputs = f"-i {voice_path} "
    if has_music: audio_inputs += f"-i {music_path} "
    if has_sfx: audio_inputs += f"-i {sfx_path} "

    # Audio Mix Logic
    amix_count = 1 + int(has_music) + int(has_sfx)
    audio_filter = f"[1:a]volume=1.0[v];"
    if has_music: audio_filter += "[2:a]volume=0.15[m];"
    if has_sfx: audio_filter += f"[{amix_count}:a]volume=0.8[s];"
    
    mix_inputs = "[v][m]" if has_music else "[v]"
    if has_sfx: mix_inputs += "[s]"
    audio_filter += f"{mix_inputs}amix=inputs={amix_count}:duration=first[a]"

    cmd = f"ffmpeg -y {video_input} {audio_inputs} -filter_complex \"{audio_filter};[0:v]{video_filter},{','.join(draw_filters)}[outv]\" -map \"[outv]\" -map \"[a]\" -t {duration} -c:v libx264 -preset superfast -crf 23 output/final.mp4"
    
    subprocess.run(cmd, shell=True)

def upload_logic(path, caption):
    # This remains the same as before, using Catbox for the public URL
    if not INSTA_TOKEN or not INSTA_ID:
        print("💡 No API keys found. Download the video from GitHub Artifacts.")
        return
    
    # [Insert the Catbox + Insta API logic from previous message here]
    print(f"Attempting upload for: {caption[:20]}...")

async def main():
    print("🚀 Agent Starting...")
    data = await generate_content()
    voice_path, duration = await create_voice(data['script'])
    render_video(data, voice_path, duration)
    upload_logic("output/final.mp4", f"{data['caption']}\n{data['hashtags']}")
    print("✅ Process Finished.")

if __name__ == "__main__":
    asyncio.run(main())
