import os, requests, time

# 1. Get environment variables securely
HF_TOKEN = os.environ.get('HF_TOKEN')
prompt = os.environ.get('PROMPT')

if not HF_TOKEN:
    print("Error: HF_TOKEN secret is missing! Please add it in GitHub Settings.")
    exit(1)

print(f"Generating image for: {prompt}")

# 2. Call Hugging Face API (UPDATED URL to the new router format)
hf_url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

# Simple retry loop in case the HF model is waking up
for attempt in range(5):
    response = requests.post(hf_url, headers=headers, json={"inputs": prompt})
    if response.status_code == 200:
        break
    print(f"Model loading or busy (Status {response.status_code}). Retrying in 10 seconds...")
    time.sleep(10) 

if response.status_code != 200:
    print(f"Hugging Face API Error: {response.text}")
    exit(1)

# 3. Save the image to a local folder named "images"
os.makedirs("images", exist_ok=True)
filename = f"images/generated_{int(time.time())}.png"

with open(filename, "wb") as file:
    file.write(response.content)

print(f"Successfully generated and saved {filename}!")
