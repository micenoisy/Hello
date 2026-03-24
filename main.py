import os, json, random, asyncio, subprocess, re, requests, time
import whisper
from edge_tts import Communicate

# [1] SETUP & AUDIT
OR_KEY = os.getenv("OPENROUTER_API_KEY")
for f in ['assets', 'templates', 'output']: os.makedirs(f, exist_ok=True)

def audit():
    print("🔍 --- SYSTEM AUDIT ---")
    f_ok = os.path.exists("assets/font.ttf")
    ts = [f for f in os.listdir('templates') if f.endswith('.mp4')]
    print(f"Font: {'✅' if f_ok else '❌'} | Templates: {len(ts)}")
    return ts

# [2] OPENROUTER SCRIPT (Llama 3.1 - Free & Reliable)
async def get_script():
    print("🧠 AI: Generating Script via OpenRouter...")
    try:
        with open('config.json', 'r') as f: cfg = json.load(f)
        topic = random.choice(cfg['topics'])
        res = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OR_KEY}"},
            data=json.dumps({
                "model": "meta-llama/llama-3.1-8b-instruct:free",
                "messages": [{"role": "user", "content": f"Write a 18s dark psychology script about {topic}. Aggressive hook. Return ONLY JSON: {{'script': '...', 'caption': '...', 'hashtags': '...'}}"}]
            })
        )
        content = res.json()['choices'][0]['message']['content']
        m = re.search(r'\{.*\}', content, re.DOTALL)
        return json.loads(m.group()), cfg
    except Exception as e:
        print(f"⚠️ AI FAIL: {e}. Using Fallback.")
        return {"script": "THE MOST DANGEROUS PERSON WATCHES EVERYTHING. THEY KNOW YOUR MOVE. THIS IS WHY YOU NEVER REVEAL THE TRUTH."}, {"power_words": ["dangerous"]}

# [3] AUDIO: VOICE -> TRIM -> WHISPER SYNC
async def process_audio(text):
    print("🎙️ AUDIO: Generating Perfect Voiceover...")
    raw_p, clean_p = "assets/raw.mp3", "assets/voice.mp3"
    
    # Generate Voice (Christopher Settings Preserved)
    c = Communicate(text, "en-US-ChristopherNeural", rate="+5%", pitch="-10Hz")
    await c.save(raw_p)
    
    # 1. TRIM SILENCE FIRST
    print("✂️ AUDIO: Trimming Silence...")
    subprocess.run(["ffmpeg", "-y", "-i", raw_p, "-af", "silenceremove=1:0:-50dB", clean_p], capture_output=True)
    
    # 2. WHISPER TRANSCRIBE (Local, No API)
    print("👂 WHISPER: Transcribing for Micro-Sync...")
    model = whisper.load_model("tiny") # Tiny is extremely fast and accurate for 20s
    result = model.transcribe(clean_p, word_timestamps=True)
    
    word_data = []
    for segment in result['segments']:
        for word in segment['words']:
            word_data.append({
                "w": word['word'].strip().upper(),
                "s": word['start'],
                "e": word['end']
            })
    
    with open("assets/subs.json", "w") as f: json.dump(word_data, f)
    dur = result['segments'][-1]['end']
    return clean_p, dur

# [4] RENDER: DYNAMIC WORD-BY-WORD
def render(data, cfg, vp, dur, ts):
    print(f"🎬 VIDEO: Rendering Reel ({round(dur, 2)}s)...")
    if ts:
        vi = ["-stream_loop", "-1", "-i", f"templates/{random.choice(ts)}"]
        vb = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,vignette=PI/4"
    else:
        vi = ["-f", "lavfi", "-i", "color=c=0x0a0a0a:s=1080x1920:d=1"]
        vb = "vignette=PI/3"
    
    with open("assets/subs.json", "r") as f: bd = json.load(f)
    font = f"fontfile='assets/font.ttf':" if os.path.exists("assets/font.ttf") else ""
    draw = []
    
    for i, it in enumerate(bd):
        s, e, w = it["s"], it["e"], it["w"].replace("'", "").replace(".", "")
        cl = "yellow" if any(pw.lower() in w.lower() for pw in cfg.get('power_words', [])) else "white"
        if i == 0: cl = "red"
        
        # Hormozi Pop Animation
        sz = f"if(lt(t,{s}),0,if(lt(t,{s}+0.06),175,145))"
        
        # Stacked Subtitles (Glow/Shadow + Main)
        draw.append(f"drawtext=text='{w}':{font}fontcolor=black@0.9:fontsize='{sz}+15':x=(w-text_w)/2+8:y=(h-text_h)/2+8:enable='between(t,{s},{e})'")
        draw.append(f"drawtext=text='{w}':{font}fontcolor={cl}:fontsize='{sz}':x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{s},{e})'")

    v_filt = f"[0:v]{vb}"
    if draw: v_filt += "," + ",".join(draw)
    v_filt += "[vout]"

    cmd = ["ffmpeg", "-y"] + vi + ["-i", vp] + [
        "-filter_complex", f"{v_filt};[1:a]volume=1.8,loudnorm[aout]",
        "-map", "[vout]", "-map", "[aout]", "-t", str(dur),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "output/final.mp4"
    ]
    subprocess.run(cmd)

async def main():
    ts = audit()
    d, cfg = await get_script()
    vp, dur = await process_audio(d['script'])
    render(d, cfg, vp, dur, ts)
    if os.path.exists("output/final.mp4"): 
        print(f"✅ SUCCESS: Perfectly synced Reel ready.")

if __name__ == "__main__":
    asyncio.run(main())    am = "[1:a]volume=1.8,loudnorm[aout]"

    cmd = ["ffmpeg", "-y"] + vi + ai + ["-filter_complex", f"{v_filt};{am}", "-map", "[vout]", "-map", "[aout]", "-t", str(dur), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "output/final.mp4"]
    subprocess.run(cmd)

async def main():
    ts = audit()
    d, cfg = await get_script()
    vp, dur = await get_audio(d['script'])
    render(d, cfg, vp, dur, ts)
    if os.path.exists("output/final.mp4"): 
        print(f"✅ SUCCESS: Perfectly synced Reel ready ({round(dur, 2)}s)")

if __name__ == "__main__":
    asyncio.run(main())
