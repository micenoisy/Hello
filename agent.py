import os, requests, time, zipfile, json
import urllib.parse

# 1. Load prompts from JSON file
json_file = "prompts.json"
if not os.path.exists(json_file):
    print(f"Error: {json_file} not found! Please create it in your repository.")
    exit(1)

with open(json_file, "r") as f:
    data = json.load(f)

# Read the model choice, default to 'flux' if none is provided
model_choice = data.get("model", "flux").strip()
style_prefix = data.get("style_prefix", "").strip()
seed = data.get("seed", 42)
prompts = data.get("prompts", [])

if not prompts:
    print("No prompts found in JSON.")
    exit(1)

print(f"--- USING AI MODEL: {model_choice.upper()} ---")

os.makedirs("images", exist_ok=True)
generated_files = []

# 2. Generate Images via Pollinations API
for i, base_prompt in enumerate(prompts):
    full_prompt = f"{style_prefix} {base_prompt}" if style_prefix else base_prompt
    print(f"\n[{i+1}/{len(prompts)}] Generating: {full_prompt}")
    
    encoded_prompt = urllib.parse.quote(full_prompt)
    
    # We now pass the &model= parameter to switch AI engines!
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed}&width=1280&height=720&nologo=true&model={model_choice}"
    
    success = False
    for attempt in range(5):
        try:
            response = requests.get(url, timeout=60)
            if response.status_code == 200:
                filename = f"images/frame_{str(i).zfill(4)}.png"
                with open(filename, "wb") as f:
                    f.write(response.content)
                generated_files.append(filename)
                print(f"Saved {filename}")
                success = True
                break
            else:
                print(f"Server returned {response.status_code}. Retrying in 5s...")
        except Exception as e:
            print(f"Request failed: {e}. Retrying in 5s...")
        
        time.sleep(5)
        
    if not success:
        print(f"Failed to generate image {i+1} after 5 attempts.")

# 3. Create Zip File
zip_filename = "generated_images.zip"
with zipfile.ZipFile(zip_filename, 'w') as zipf:
    for file in generated_files:
        zipf.write(file, os.path.basename(file))

print(f"\nSuccess! Zipped {len(generated_files)} video frames into {zip_filename}.")
