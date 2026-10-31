import os
from random import randint
from time import sleep
from PIL import Image
from diffusers import StableDiffusionPipeline
import torch

# -----------------------------
# CONFIG
# -----------------------------
DATA_FOLDER = "Data"
os.makedirs(DATA_FOLDER, exist_ok=True)
NUM_IMAGES = 3  # Number of images per prompt

# -----------------------------
# Setup Stable Diffusion
# -----------------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16 if device=="cuda" else torch.float32
)
pipe.to(device)

# -----------------------------
# Function to generate a single image
# -----------------------------
def generate_single_image(prompt, seed=None):
    generator = torch.Generator(device).manual_seed(seed or randint(0,1_000_000))
    image = pipe(prompt, generator=generator).images[0]
    return image

# -----------------------------
# Function to save & open images
# -----------------------------
def save_and_open_images(prompt, images):
    prompt_safe = prompt.replace(" ", "_")
    for i, img in enumerate(images, start=1):
        file_path = os.path.join(DATA_FOLDER, f"{prompt_safe}{i}.jpg")
        img.save(file_path)
        try:
            img.show()
        except Exception as e:
            print(f"Cannot open {file_path}: {e}")

# -----------------------------
# Main function
# -----------------------------
def main():
    print("⚡ Hugging Face Image Generator (Synchronous CPU-friendly)")
    while True:
        prompt = input("\nEnter your prompt (or 'exit' to quit): ").strip()
        if prompt.lower() == "exit":
            break
        if not prompt:
            print("Prompt cannot be empty!")
            continue

        enhanced_prompt = f"{prompt}, ultra realistic, UHD, crisp details, 8K, masterpiece"
        print(f"\n⚡ Enhanced Prompt: {enhanced_prompt}")

        images = []
        for i in range(NUM_IMAGES):
            print(f"🚀 GENERATING IMAGE {i+1}/{NUM_IMAGES} ...")
            try:
                img = generate_single_image(enhanced_prompt)
                images.append(img)
                print(f"✅ IMAGE {i+1} generated")
            except Exception as e:
                print(f"❌ Failed to generate image {i+1}: {e}")

        save_and_open_images(prompt, images)
        print("🔄 Done! Images saved in Data/ folder.")

if __name__ == "__main__":
    main()
