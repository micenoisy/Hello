import os, json, asyncio, subprocess, whisper, time
from edge_tts import Communicate
from ai_engine import get_script  # <--- IMPORTING THE BRAIN

# [1] SETUP
for f in ['assets', 'templates', 'output']: os.makedirs(f, exist_ok=True)

# [2] AUDIO & WHISPER SYNC
async def process_audio(text):
    print("🎙️ AUDIO: Processing Voice & Whisper Sync...")
    voice_p = "assets/voice.mp3"
    # Christopher Settings: Natural, Deep, Studio Quality
    c = Communicate(text, "en-US-ChristopherNeural", rate="+0%", pitch="-4Hz")
    await c.save(voice_p)
    
    # Transcription for Micro-Sync
    model = whisper.load_model("tiny")
    result = model.transcribe(voice_p, word_timestamps=True)
    
    word_data = []
    for seg in result['segments']:
        for w in seg['words']:
            word_data.append({"w": w['word'].strip().upper(), "s": w['start'], "e": w['end']})
    
    with open("assets/subs.json", "w") as f: json.dump(word_data, f)
    return voice_p, result['segments'][-1]['end']

# [3] RENDERING ENGINE
def render(data, cfg, vp, dur):
    print(f"🎬 VIDEO: Rendering Pro Reel...")
    ts = [f for f in os.listdir('templates') if f.endswith('.mp4')]
    v_in = ["-stream_loop", "-1", "-i", f"templates/{random.choice(ts)}"] if ts else ["-f", "lavfi", "-i", "color=c=0x0a0a0a:s=1080x1920:d=1"]
    
    v_base = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,vignette=PI/4"
    with open("assets/subs.json", "r") as f: bd = json.load(f)
    font = f"fontfile='assets/font.ttf':" if os.path.exists("assets/font.ttf") else ""
    draw = []
    
    for it in bd:
        s, e, w = it["s"], it["e"], it["w"].replace("'", "").replace(".", "")
        cl = "white"
        if w.lower() in cfg.get('yellow_words', []): cl = "yellow"
        if w.lower() in cfg.get('red_words', []): cl = "red"
        sz = f"if(lt(t,{s}),0,if(lt(t,{s}+0.05),140,120))"
        # Golden Zone Subtitles
        draw.append(f"drawtext=text='{w}':{font}fontcolor=black@0.9:fontsize='{sz}+12':borderw=10:bordercolor=black:x=(w-text_w)/2:y=(h*0.65):enable='between(t,{s},{e})'")
        draw.append(f"drawtext=text='{w}':{font}fontcolor={cl}:fontsize='{sz}':x=(w-text_w)/2:y=(h*0.65):enable='between(t,{s},{e})'")

    v_filt = f"[0:v]{v_base}"
    if draw: v_filt += "," + ",".join(draw)
    
    # STUDIO MIC FILTER SETTINGS
    studio_af = "highpass=f=100,bass=g=5,volume=1.8,loudnorm"

    cmd = ["ffmpeg", "-y"] + v_in + ["-i", vp] + [
        "-filter_complex", f"{v_filt}[vout];[1:a]{studio_af}[aout]",
        "-map", "[vout]", "-map", "[aout]", "-t", str(dur),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "output/final.mp4"
    ]
    subprocess.run(cmd)

# [4] MAIN ORCHESTRATOR
async def main():
    print("🚀 AGENT INITIATED...")
    
    # Call the isolated AI Engine
    data, cfg = await get_script()
    
    # Process Audio & Sync
    vp, dur = await process_audio(data['script'])
    
    # Render Video
    render(data, cfg, vp, dur)
    
    if os.path.exists("output/final.mp4"): 
        print(f"✅ SUCCESS: Studio-Mastered Reel Ready ({round(dur, 2)}s)")

if __name__ == "__main__":
    import random # Needed for template selection
    asyncio.run(main())    if os.path.exists("output/final.mp4"): 
        print(f"✅ SUCCESS: Studio Reel Ready ({round(dur, 2)}s)")

if __name__ == "__main__":
    asyncio.run(main())
