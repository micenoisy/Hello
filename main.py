import os, json, asyncio, subprocess, whisper, time, random
from edge_tts import Communicate
from ai_engine import get_script

# [1] SETUP
for f in ['assets', 'templates', 'output']: os.makedirs(f, exist_ok=True)

async def process_audio(text):
    print("🎙️ AUDIO: Generating Natural Voice & Whisper Sync...")
    vp = "assets/voice.mp3"
    c = Communicate(text, "en-US-ChristopherNeural", rate="+10%", pitch="-10Hz")
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

def render(data, cfg, vp, dur):
    print(f"🎬 VIDEO: Rendering High-Dynamic Reel...")
    ts = [f for f in os.listdir('templates') if f.endswith('.mp4')]
    v_in = ["-stream_loop", "-1", "-i", f"templates/{random.choice(ts)}"] if ts else ["-f", "lavfi", "-i", "color=c=0x0a0a0a:s=1080x1920:d=1"]
    v_base = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,vignette=PI/4"
    
    with open("assets/subs.json", "r") as f: bd = json.load(f)
    font = f"fontfile='assets/font.ttf':" if os.path.exists("assets/font.ttf") else ""
    draw = []
    
    # 🔴 RED WORDS (Danger / Hooks)
    red_list = ["never", "dangerous", "truth", "stop", "illegal", "warning", "weakness", "trap", "control", "betrayal", "destroy", "secret", "watch", "fear", "death", "blood", "pain", "liar", "exposed", "accuse", "lethal"]
    
    # 🟡 YELLOW WORDS (Power / Action)
    yellow_list = ["person", "everything", "move", "reveal", "calculating", "watches", "know", "silence", "power", "money", "win", "hidden", "mind", "brain", "trick", "tactic", "dark", "psychology", "expert", "master", "rule", "law", "obsessed", "focus", "success", "failure", "life", "world", "people", "alpha", "sigma", "loyalty", "respect", "honor", "trust", "action", "growth", "money", "rich", "poor", "strong", "fast", "smart", "wisdom", "knowledge", "ego", "pride", "sin", "virtue", "grace", "mercy", "justice", "freedom", "path", "destination", "journey", "future", "forever", "always", "today", "tomorrow"]

    for i, it in enumerate(bd):
        s, e, w = it["s"], it["e"], it["w"].replace("'", "").replace(".", "")
        
        # DYNAMIC COLOR LOGIC
        cl = "white"
        if w.lower() in yellow_list: cl = "yellow"
        if w.lower() in red_list or i == 0: cl = "red" # Always first word red
        
        # AGGRESSIVE POP SIZE: Hits at 160 settles at 135
        sz = f"if(lt(t,{s}),0,if(lt(t,{s}+0.05),160,135))"
        
        # PRO LAYERS: Black Outline + Color Text
        draw.append(f"drawtext=text='{w}':{font}fontcolor=black@0.9:fontsize='{sz}+15':borderw=12:bordercolor=black:x=(w-text_w)/2:y=(h*0.65):enable='between(t,{s},{e})'")
        draw.append(f"drawtext=text='{w}':{font}fontcolor={cl}:fontsize='{sz}':x=(w-text_w)/2:y={h*0.65}:enable='between(t,{s},{e})'")

    v_filt = f"[0:v]{v_base}"
    if draw: v_filt += "," + ",".join(draw)
    
    # Studio Mic Filter
    studio_af = "highpass=f=100,bass=g=5,volume=1.8,loudnorm"

    cmd = ["ffmpeg", "-y"] + v_in + ["-i", vp] + [
        "-filter_complex", f"{v_filt}[vout];[1:a]{studio_af}[aout]",
        "-map", "[vout]", "-map", "[aout]", "-t", str(dur),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "output/final.mp4"
    ]
    subprocess.run(cmd)

async def main():
    print("🎬 AGENT STARTING (Llama 3.3 70B Edition)...")
    data, cfg = await get_script()
    vp, dur = await process_audio(data['script'])
    render(data, cfg, vp, dur)
    if os.path.exists("output/final.mp4"): 
        print(f"✅ SUCCESS: High-Dynamic Reel Generated.")

if __name__ == "__main__":
    asyncio.run(main())
