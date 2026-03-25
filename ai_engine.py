import os, json, random, requests, re

API_KEY = os.getenv("GROQ_API_KEY")
URL = "https://api.groq.com/openai/v1/chat/completions"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

async def get_script():
    print("🚀 AI_ENGINE: Calling Llama 3.3 70B (Flagship Edition)...")
    try:
        with open('config.json', 'r') as f: cfg = json.load(f)
        topic = random.choice(cfg['topics'])
        
        # PREDATORY VIRAL PROMPT
        prompt = f"""
        Act as a Master of Dark Psychology. Create a 15-second viral script about {topic}.
        
        Rules for Millions of Views:
        - Line 1: A 'Stop the Scroll' hook. Must be a direct accusation like 'YOU ARE BEING...' or 'THEY USED THIS TO...'
        - Body: Explain one lethal psychological hack. Max 3 punchy sentences.
        - Loop: End with 'THE REASON IS...' to loop perfectly.
        - Output: Return ONLY raw JSON. NO markdown. NO preamble.
        
        Format:
        {{
            "script": "...",
            "caption": "...",
            "hashtags": "..."
        }}
        """

        payload = {
            "model": "llama-3.3-70b-versatile", # UPGRADED TO LLAMA 3.3 70B
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "response_format": {"type": "json_object"}
        }

        response = requests.post(URL, headers=HEADERS, json=payload)
        res_json = response.json()
        
        # SAFETY CHECK
        if "choices" not in res_json:
            print(f"❌ GROQ ERROR: {res_json}")
            raise ValueError("API Response Invalid")
            
        content = res_json["choices"][0]["message"]["content"]
        script_data = json.loads(content)
        return script_data, cfg

    except Exception as e:
        print(f"⚠️ AI_ENGINE FAIL: {e}. Using Emergency Loop.")
        return {
            "script": "THE MOST DANGEROUS PERSON WATCHES EVERYTHING IN SILENCE. THEY KNOW YOUR WEAKNESS. THIS IS WHY YOU MUST NEVER...",
            "caption": "Watch the quiet ones.",
            "hashtags": "#darkpsychology #manipulation"
        }, cfg
