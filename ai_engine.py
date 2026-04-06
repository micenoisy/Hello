import os, json, random, requests, re

# [1] GROQ CONFIG
API_KEY = os.getenv("GROQ_API_KEY")
URL = "https://api.groq.com/openai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

async def get_script():
    print("🚀 AI_ENGINE: Calling Groq (Llama 3.1 8B Instant)...")
    try:
        with open('config.json', 'r') as f: cfg = json.load(f)
        topic = random.choice(cfg['topics'])
        
        # AGGRESSIVE VIRAL PROMPT
        prompt = f"""
        Act as a Master of Dark Psychology and Viral Storytelling. 
        Create a 15-18 second script for a viral Reel about {topic}.
        
        Rules for Millions of Views:
        - Line 1 (The Hook): Must be an aggressive accusation or a terrifying warning.
        - Body: Use 'The Shadow' perspective. Reveal a tactic that makes the viewer feel exposed.
        - Loop: The final sentence must be a cliffhanger that flows perfectly into the first word.
        - Style: No 'Hello' or 'Welcome'. Start with the knife.
        
        Return ONLY valid JSON:
        {{
            "script": "...",
            "caption": "...",
            "hashtags": "..."
        }}
        """

        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8,
            "response_format": {"type": "json_object"} # Forces Groq to return clean JSON
        }

        response = requests.post(URL, headers=HEADERS, json=payload)
        data = response.json()
        
        script_data = json.loads(data["choices"][0]["message"]["content"])
        print(f"✅ AI_ENGINE: Viral Script Generated for '{topic}'")
        return script_data, cfg

    except Exception as e:
        print(f"⚠️ AI_ENGINE FAIL: {e}")
        return {
            "script": "They are already controlling you, and you still think you are in charge. Every time you hesitate, every time you overthink, that is not your real voice. That is conditioning, built slowly so you doubt yourself and stay quiet and predictable. You were trained without even noticing, and the one who did it is still around you every single day. And the worst part is, they are about to reveal themselves right now… they are—",
            "caption": "Silence is power.",
            "hashtags": "#darkpsychology"
        }, {"red_words": ["dangerous", "never"], "yellow_words": ["everything", "move"]}
