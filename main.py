import os, json, random, asyncio, subprocess, re, requests, time
import whisper
from edge_tts import Communicate

# [1] SECRETS & PATHS
OR_KEY = os.getenv("OPENROUTER_API_KEY")
for f in ['assets', 'templates', 'output']: os.makedirs(f, exist_ok=True)

def audit():
    print("🔍 --- SYSTEM PERFORMANCE AUDIT ---")
    f_ok = os.path.exists("assets/font.ttf")
    ts = [f for f in os.listdir('templates') if f.endswith('.mp4')]
    print(f"Font: {'✅' if f_ok else '❌'} | Templates: {len(ts)}")
    return ts

# [2] TOP-TIER AI: LLAMA 3.3 70B (Free)
async def get_script():
    print("🧠 AI: Generating High-End Script (Llama 3.3 70B)...")
    try:
        with open('config.json', 'r') as f: cfg = json.load(f)
        topic = random.choice(cfg['topics'])
        
        # Meta Llama 3.3 70B Instruct (Free)
        res = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"},
            data=json.dumps({
                "model": "meta-llama/llama-3.3-70b-instruct:free",
                "messages": [{
                    "role": "user", 
                    "content": f"Write a 15-20s dark psychology script about {topic}. Aggressive hook. Use periods and commas for natural pauses. The last word must loop to the first word. Return ONLY JSON: {{'script': '...', 'caption': '...', 'hashtags': '...'}}"
                }]
            })
        )
        data = res.json()['choices'][0]['message']['content']
        m = re.search(r'\{.*\}', data, re.DOTALL)
        return json.loads(m.group()), cfg
    except Exception as e:
        print(f"⚠️ AI FAIL ({e}): Using Fallback.")
        return {"script": "He always smiled at the right moments, nodded at the right words, and remembered details no one else cared about; the kind of man people trusted without knowing why, the kind of presence that felt safe until it wasn’t. He learned early that people reveal themselves in fragments, a hesitation before answering, a flicker in the eyes, a nervous habit repeated under pressure; he collected those fragments like a hunter tracking footprints, slowly building a map of every weakness hidden beneath polite conversations. At first, it was harmless, just observation, just curiosity, but curiosity turned into control, and control tasted intoxicating. He would plant small ideas, barely noticeable, a suggestion here, a doubt there, watching as people slowly changed their decisions, convinced they were acting on their own thoughts. The real thrill was not in forcing anyone, but in guiding them so subtly that they never realized they were being led. One friend began to distrust another after a few carefully timed remarks; a colleague quit his job after being nudged toward imagined failures; a relationship collapsed because he knew exactly which insecurities to amplify. He never raised his voice, never showed anger, because he understood that the quietest manipulations leave the deepest scars. Over time, he stopped seeing people as individuals and started seeing them as systems, predictable patterns waiting to be exploited. Yet something shifted the day he caught his own reflection and felt nothing; no guilt, no pride, just emptiness staring back at him like a void that had quietly consumed everything human inside. In that moment, he realized the final truth of his game, that control over others had cost him control over himself, and the mind he had mastered so well had become a prison with no exit."}, {"red_words": ["never", "dangerous", "truth"], "yellow_words": ["everything", "move"]}

# [3] NATURAL AUDIO: VOICE -> GENTLE EDGE-TRIM -> WHISPER SYNC
async def process_audio(text):
    print("🎙️ AUDIO: Generating Natural Christopher Voice...")
    raw_p, clean_p = "assets/raw.mp3", "assets/voice.mp3"
    
    # Natural Settings: +5% speed is perfect for human-like urgency
    c = Communicate(text, "en-US-ChristopherNeural", rate="+5%", pitch="-10Hz")
    await c.save(raw_p)
    
    # GENTLE EDGE TRIMMING (Trims leading/trailing silence only)
    # This keeps the human rhythm of punctuation (commas/periods) intact
    subprocess.run([
        "ffmpeg", "-y", "-i", raw_p, 
        "-af", "silenceremove=start_periods=1:start_threshold=-50dB:stop_periods=1:stop_threshold=-50dB", 
        clean_p
    ], capture_output=True)
    
    # WHISPER MICRO-SYNC (Transcribes final audio for 100% precision)
    print("👂 WHISPER: Transcribing final audio for perfect sync...")
    model = whisper.load_model("tiny")
    result = model.transcribe(clean_p, word_timestamps=True)
    
    word_data = []
    for seg in result['segments']:
        for w in seg['words']:
            word_data.append({"w": w['word'].strip().upper(), "s": w['start'], "e": w['end']})
    
    with open("assets/subs.json", "w") as f: json.dump(word_data, f)
    return clean_p, result['segments'][-1]['end']

# [4] SLEEK SUBTITLE RENDER (Refined Size & Position)
def render(data, cfg, vp, dur, ts):
    print(f"🎬 VIDEO: Rendering Pro Reel ({round(dur, 2)}s)...")
    v_in = ["-stream_loop", "-1", "-i", f"templates/{random.choice(ts)}"] if ts else ["-f", "lavfi", "-i", "color=c=0x0a0a0a:s=1080x1920:d=1"]
    v_base = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,vignette=PI/4"
    
    with open("assets/subs.json", "r") as f: bd = json.load(f)
    font = f"fontfile='assets/font.ttf':" if os.path.exists("assets/font.ttf") else ""
    draw = []
    
    # Position: Lower-Middle (65% height)
    pos_y = "(h*0.65)"
    
    for it in bd:
        s, e, w = it["s"], it["e"], it["w"].upper().replace("'", "").replace(".", "").replace(",", "")
        
        # Color Engine
        cl = "white"
        if w.lower() in cfg.get('yellow_words', []): cl = "yellow"
        if w.lower() in cfg.get('red_words', []): cl = "red"
        
        # SLEEK FONT SIZE (Hormozi Snap: 140 -> 120)
        sz = f"if(lt(t,{s}),0,if(lt(t,{s}+0.05),140,120))"
        
        # PRO STACKED SUBTITLES (Black Glow + Styled Text)
        # Layer 1: Thick Black Shadow Stroke
        draw.append(f"drawtext=text='{w}':{font}fontcolor=black@0.9:fontsize='{sz}+12':borderw=10:bordercolor=black:x=(w-text_w)/2:y={pos_y}:enable='between(t,{s},{e})'")
        # Layer 2: Main Styled Text
        draw.append(f"drawtext=text='{w}':{font}fontcolor={cl}:fontsize='{sz}':x=(w-text_w)/2:y={pos_y}:enable='between(t,{s},{e})'")

    v_filt = f"[0:v]{v_base}"
    if draw: v_filt += "," + ",".join(draw)
    v_filt += "[vout]"

    cmd = ["ffmpeg", "-y"] + v_in + ["-i", vp] + [
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
        print(f"✅ SUCCESS: Natural Rhythm Reel Ready ({round(dur, 2)}s)")

if __name__ == "__main__":
    asyncio.run(main())    cmd = ["ffmpeg", "-y"] + v_in + ["-i", vp] + [
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
        print(f"✅ SUCCESS: High-Paced Sync Reel Ready ({round(dur, 2)}s)")

if __name__ == "__main__":
    asyncio.run(main())
