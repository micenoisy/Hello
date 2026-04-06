import os, json, asyncio, subprocess, whisper, time, random
from edge_tts import Communicate
from ai_engine import get_script  # IMPORTING GROQ BRAIN

# [1] SETUP
for f in ['assets', 'templates', 'output']: os.makedirs(f, exist_ok=True)

# [2] AUDIO & WHISPER SYNC
async def process_audio(text):
    print("🎙️ AUDIO: Generating Natural Voice & Whisper Sync...")
    vp = "assets/voice.mp3"
    # Christopher Settings: Deep & Authoritative
    c = Communicate(text, "en-US-ChristopherNeural", rate="+4%", pitch="-0Hz")
    await c.save(vp)
    
    # Micro-Sync with Local Whisper
    model = whisper.load_model("tiny")
    result = model.transcribe(vp, word_timestamps=True)
    
    word_data = []
    for seg in result['segments']:
        for w in seg['words']:
            word_data.append({"w": w['word'].strip().upper(), "s": w['start'], "e": w['end']})
    
    with open("assets/subs.json", "w") as f: json.dump(word_data, f)
    return vp, result['segments'][-1]['end']

# [3] RENDERING ENGINE
def render(data, cfg, vp, dur):
    print(f"🎬 VIDEO: Rendering Pro Reel ({round(dur, 2)}s)...")
    ts = [f for f in os.listdir('templates') if f.endswith('.mp4')]
    v_in = ["-stream_loop", "-1", "-i", f"templates/{random.choice(ts)}"] if ts else ["-f", "lavfi", "-i", "color=c=0x0a0a0a:s=1080x1920:d=1"]
    v_base = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,vignette=PI/4"
    
    with open("assets/subs.json", "r") as f: bd = json.load(f)
    font = f"fontfile='assets/font.ttf':" if os.path.exists("assets/font.ttf") else ""
    draw = []
    
    # Subtitle Style: Hormozi Pop + Lower Center Position
    for it in bd:
        s, e, w = it["s"], it["e"], it["w"].replace("'", "").replace(".", "")
        cl = "white"
        if w.lower() in cfg.get('yellow_words', []): cl = "yellow"
        if w.lower() in cfg.get('red_words', []): cl = "red"
        
        # Dynamic Size Pop
        sz = f"if(lt(t,{s}),0,if(lt(t,{s}+0.05),145,125))"
        
        # Layer 1: Stroke Layer | Layer 2: Color Layer
        draw.append(f"drawtext=text='{w}':{font}fontcolor=black@0.9:fontsize='{sz}+15':borderw=10:bordercolor=black:x=(w-text_w)/2:y=(h*0.65):enable='between(t,{s},{e})'")
        draw.append(f"drawtext=text='{w}':{font}fontcolor={cl}:fontsize='{sz}':x=(w-text_w)/2:y=(h*0.65):enable='between(t,{s},{e})'")

    v_filt = f"[0:v]{v_base}"
    if draw: v_filt += "," + ",".join(draw)
    
    # STUDIO MIC FILTER: Deep Bass + High Clarity + No Silence Clipping
    studio_af = "highpass=f=100,bass=g=5,volume=1.8,loudnorm"

    cmd = ["ffmpeg", "-y"] + v_in + ["-i", vp] + [
        "-filter_complex", f"{v_filt}[vout];[1:a]{studio_af}[aout]",
        "-map", "[vout]", "-map", "[aout]", "-t", str(dur),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "output/final.mp4"
    ]
    subprocess.run(cmd)

async def main():
    print("🚀 AGENT STARTING (Groq Llama 3.1 Edition)...")
    data, cfg = await get_script()
    vp, dur = await process_audio(data['script'])
    render(data, cfg, vp, dur)
    if os.path.exists("output/final.mp4"): 
        print(f"✅ SUCCESS: Viral Reel Generated.")

if __name__ == "__main__":
    asyncio.run(main())
