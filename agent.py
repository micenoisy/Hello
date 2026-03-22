import os, requests, time

# 1. HARDCODE YOUR API KEY HERE
HF_TOKEN = "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" 

# 2. Get the prompt typed into the GitHub Actions UI
prompt = os.environ.get('PROMPT')
print(f"Generating image for: {prompt}")

# 3. Call Hugging Face API (Using FLUX for high quality, fast generation)
hf_url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

# Simple retry loop in case the HF model is waking up
for attempt in range(5):
    response = requests.post(hf_url, headers=headers, json={"inputs": prompt})
    if response.status_code == 200:
        break
    time.sleep(10) # Wait 10 seconds and retry if model is loading

if response.status_code != 200:
    print(f"Hugging Face API Error: {response.text}")
    exit(1)

# 4. Save the image to a local folder named "images"
os.makedirs("images", exist_ok=True)
filename = f"images/generated_{int(time.time())}.png"

with open(filename, "wb") as file:
    file.write(response.content)

print(f"Successfully generated and saved {filename}!")
