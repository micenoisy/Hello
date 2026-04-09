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
            "script": "I heard my own voice say something I never thought. You are not in control. I froze. I did not speak. But my lips moved. Again the voice came. Turn around. I tried to resist. My body turned anyway. That was the moment I understood. It was not following me. I was following it. I ran to the mirror. I looked into my eyes. They were calm. Too calm. The voice whispered. Look closer. So I did. And then it said. You are reading this because I want you to. Now tell me. What will you do next.",
            "caption": "Silence is power.",
            "hashtags": "#darkpsychology"
        }, {"red_words": ["voice", "control", "lips", "turned", "following", "mirror", "calm", "closer", "reading", "next"], "yellow_words": ["heard", "froze", "speak", "resist", "understood", "ran", "looked", "whispered", "want"]}
