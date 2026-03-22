import os, requests, time, zipfile, json

HF_TOKEN = os.environ.get('HF_TOKEN')
if not HF_TOKEN:
    print("Error: HF_TOKEN secret is missing!")
    exit(1)

# 1. Load prompts from JSON file
json_file = "prompts.json"
if not os.path.exists(json_file):
    print(f"Error: {json_file} not found! Please create it in your repository.")
    exit(1)

with open(json_file, "r") as f:
    data = json.load(f)

style_prefix = data.get("style_prefix", "").strip()
seed = data.get("seed", 42) # Fixed seed for video consistency!
prompts = data.get("prompts", [])

if not prompts:
    print("No prompts found in JSON.")
    exit(1)

# 2. Setup Hugging Face API
hf_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

os.makedirs("images", exist_ok=True)
generated_files = []

# 3. Generate Images
for i, base_prompt in enumerate(prompts):
    full_prompt = f"{style_prefix} {base_prompt}" if style_prefix else base_prompt
    print(f"\n[{i+1}/{len(prompts)}] Generating: {full_prompt}")
    
    # We pass the seed parameter to Hugging Face to keep the art style highly consistent
    payload = {
        "inputs": full_prompt,
        "parameters": {"seed": seed} 
    }
    
    # Retry loop
    for attempt in range(5):
        response = requests.post(hf_url, headers=headers, json=payload)
        if response.status_code == 200:
            break
        print(f"Model busy (Status {response.status_code}). Retrying in 10s...")
        time.sleep(10)
        
    if response.status_code == 200:
        # Name sequentially (frame_0000.png, frame_0001.png) for easy video editing
        filename = f"images/frame_{str(i).zfill(4)}.png"
        with open(filename, "wb") as f:
            f.write(response.content)
        generated_files.append(filename)
        print(f"Saved {filename}")
    else:
        print(f"Failed to generate image {i+1}: {response.text}")

# 4. Create Zip File
zip_filename = "generated_images.zip"
with zipfile.ZipFile(zip_filename, 'w') as zipf:
    for file in generated_files:
        zipf.write(file, os.path.basename(file))

print(f"\nSuccess! Zipped {len(generated_files)} video frames into {zip_filename}.")
