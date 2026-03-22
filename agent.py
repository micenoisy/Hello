import os, requests, time, zipfile

# 1. Get environment variables
HF_TOKEN = os.environ.get('HF_TOKEN')
style_prefix = os.environ.get('STYLE_PREFIX', '').strip()
prompts_input = os.environ.get('PROMPTS', '')

if not HF_TOKEN:
    print("Error: HF_TOKEN secret is missing!")
    exit(1)

# Split the multi-line input into separate prompts (ignoring empty lines)
prompts = [p.strip() for p in prompts_input.split('\n') if p.strip()]

if not prompts:
    print("No prompts provided.")
    exit(1)

# 2. Setup Hugging Face API
hf_url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

os.makedirs("images", exist_ok=True)
generated_files = []

# 3. Loop through every prompt and generate an image
for i, base_prompt in enumerate(prompts):
    # Combine the style prefix with the specific prompt to keep consistency
    full_prompt = f"{style_prefix} {base_prompt}" if style_prefix else base_prompt
    
    print(f"\n[{i+1}/{len(prompts)}] Generating: {full_prompt}")
    
    # Retry loop in case the model is busy
    for attempt in range(5):
        response = requests.post(hf_url, headers=headers, json={"inputs": full_prompt})
        if response.status_code == 200:
            break
        print(f"Model busy (Status {response.status_code}). Retrying in 10s...")
        time.sleep(10)
        
    if response.status_code == 200:
        filename = f"images/image_{i+1}_{int(time.time())}.png"
        with open(filename, "wb") as f:
            f.write(response.content)
        generated_files.append(filename)
        print(f"Saved {filename}")
    else:
        print(f"Failed to generate image {i+1}: {response.text}")

# 4. Create a Zip File of all generated images
zip_filename = "generated_images.zip"
with zipfile.ZipFile(zip_filename, 'w') as zipf:
    for file in generated_files:
        # Add file to zip (stripping the 'images/' folder path inside the zip)
        zipf.write(file, os.path.basename(file))

print(f"\nSuccess! Zipped {len(generated_files)} images into {zip_filename}.")
