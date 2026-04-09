import os
from PIL import Image

def extract_gifs(directory):
    for filename in os.listdir(directory):
        if filename.lower().endswith(".gif"):
            filepath = os.path.join(directory, filename)
            base_name = os.path.splitext(filename)[0]
            try:
                img = Image.open(filepath)
                frames = getattr(img, "n_frames", 1)
                for i in range(frames):
                    img.seek(i)
                    rgba = img.convert("RGBA")
                    out_path = os.path.join(directory, f"{base_name}_f{i}.png")
                    rgba.save(out_path)
                print(f"Extracted {frames} frames from {filename}")
            except Exception as e:
                print(f"Failed to extract {filename}: {e}")

if __name__ == "__main__":
    img_dir = os.path.join(os.path.dirname(__file__), "images")
    if os.path.exists(img_dir):
        extract_gifs(img_dir)
    else:
        print("Images directory not found!")
