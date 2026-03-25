import os, json, random, requests, re

# Load OpenRouter Key
OR_KEY = os.getenv("OPENROUTER_API_KEY")

async def get_script():
    print("🧠 AI_ENGINE: Processing viral logic...")
    try:
        # 1. Load Topics & Power Words
        with open('config.json', 'r') as f: 
            cfg = json.load(f)
        
        topic = random.choice(cfg['topics'])
        
        # 2. Call OpenRouter (Llama 3.3 70B)
        # Added a highly aggressive 'Retention-First' prompt
        res = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OR_KEY}",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": "meta-llama/llama-3.3-70b-instruct:free",
                "messages": [{
                    "role": "user", 
                    "content": f"""
                    Act as a Dark Psychology & Short-Form Content Expert. 
                    Write a 15-18 second script about {topic}.
                    
                    Structure:
                    - 0-3s: AN EXTREME HOOK. Use words like 'LETHAL', 'DANGEROUS', 'SECRET'.
                    - 3-15s: 3 short, punchy facts. Max 5 words per sentence.
                    - 15-18s: A loop sentence that connects back to the start.
                    
                    Tone: Dark, mysterious, aggressive. No emojis.
                    Return ONLY valid JSON: 
                    {{"script": "...", "caption": "...", "hashtags": "..."}}
                    """
                }]
            })
        )
        
        response_data = res.json()
        if 'choices' not in response_data:
            raise ValueError(f"AI API Error: {response_data}")
            
        content = response_data['choices'][0]['message']['content']
        
        # 3. Clean and parse JSON
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        final_data = json.loads(json_match.group())
        
        print(f"✅ AI_ENGINE: Script ready for topic: {topic}")
        return final_data, cfg

    except Exception as e:
        print(f"⚠️ AI_ENGINE FAIL: {e}. Launching Emergency Fallback.")
        # Bulletproof fallback so the automation never stops
        return {
            "script": "NEVER REVEAL YOUR NEXT MOVE, THE MOST DANGEROUS PERSON WATCHES EVERYTHING IN SILENCE, THEY KNOW THE TRUTH. AND THAT IS WHY...",
            "caption": "Silence is the ultimate weapon.",
            "hashtags": "#darkpsychology #manipulation #mindset"
        }, {"red_words": ["never", "dangerous", "truth"], "yellow_words": ["everything", "silence", "move"]}
