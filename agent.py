import os, requests, time, zipfile, json
import urllib.parse

# 1. Load prompts from JSON file
json_file = "prompts.json"
with open(json_file, "r") as f:
    data = json.load(f)

style_prefix = data.get("style_prefix", "").strip()
seed = data.get("seed", 42)
prompts = data.get("prompts", [])

os.makedirs("images", exist_ok=True)
generated_files = []

# 2. Generate Unlimited Free Images via Pollinations
for i, base_prompt in enumerate(prompts):
    full_prompt = f"{style_prefix} {base_prompt}" if style_prefix else base_prompt
    print(f"\n[{i+1}/{len(prompts)}] Generating: {full_prompt}")
    
    # URL encode the prompt so it's safe for the web request
    encoded_prompt = urllib.parse.quote(full_prompt)
    
    # Free API URL. width=1280 & height=720 is perfect for YouTube/Video!
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed}&width=1280&height=720&nologo=true"
    
    # Retry loop
    for attempt in range(5):
        response = requests.get(url)
        if response.status_code == 200:
            break
        print(f"Server busy. Retrying in 5 seconds...")
        time.sleep(5)
        
    if response.status_code == 200:
        filename = f"images/frame_{str(i).zfill(4)}.png"
        with open(filename, "wb") as f:
            f.write(response.content)
        generated_files.append(filename)
        print(f"Saved {filename}")

# 3. Create Zip File
zip_filename = "generated_images.zip"
with zipfile.ZipFile(zip_filename, 'w') as zipf:
    for file in generated_files:
        zipf.write(file, os.path.basename(file))

print(f"\nSuccess! Zipped {len(generated_files)} video frames into {zip_filename}.")
