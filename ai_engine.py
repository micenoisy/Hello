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
            "script": "Bizarre anxiety hacks my therapist taught me that actually saved my mental health
Make weird faces in the mirror until you laugh
It breaks the anxiety loop because your brain cannot feel fear and laughter at the same time
Hold ice cubes in both hands
The cold shock forces your body out of fight or flight mode almost instantly
Count backwards from one hundred by sevens
Your brain gets so focused on the numbers that the anxiety loop stops
Say thank you anxiety out loud
When you stop fighting it and accept it the feeling loses power faster
Write everything in your head somewhere safe
Getting your thoughts out helps your brain slow down and process them
Hum your favorite song out loud
The vibration calms your nervous system and makes it harder to overthink
Do one small brain task
Even a tiny action can break the freeze and bring you back into control
Text someone I am spiraling but I do not need advice
Saying it out loud to someone can break the cycle instantly
Save this for when your mind starts spiraling",
            "caption": "Silence is power.",
            "hashtags": "#darkpsychology"
        }, {"red_words": ["dangerous", "never"], "yellow_words": ["everything", "move"]}
