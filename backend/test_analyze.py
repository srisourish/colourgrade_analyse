import requests
import base64
import json
import os

API_URL = "http://127.0.0.1:8000/analyze"
IMAGE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_graded.png")
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "neutralized_preview.jpg")

def test_api():
    if not os.path.exists(IMAGE_PATH):
        print(f"Error: Test image not found at {IMAGE_PATH}")
        return
        
    print(f"Uploading {IMAGE_PATH} to {API_URL}...")
    
    with open(IMAGE_PATH, "rb") as f:
        files = {"file": (os.path.basename(IMAGE_PATH), f, "image/png")}
        try:
            response = requests.post(API_URL, files=files)
        except Exception as e:
            print(f"Failed to connect to API: {e}")
            return
            
    if response.status_code != 200:
        print(f"Error: Server returned status code {response.status_code}")
        print(response.text)
        return
        
    data = response.json()
    if not data.get("success"):
        print("Error: API reports failure.")
        return
        
    print("\n--- ESTIMATED PARAMETERS ---")
    print(json.dumps(data["parameters"], indent=2))
    
    # Save neutralized image
    neutral_b64 = data["neutralized_image"]
    if neutral_b64.startswith("data:image/jpeg;base64,"):
        b64_data = neutral_b64.split(",")[1]
        img_data = base64.b64decode(b64_data)
        with open(OUTPUT_PATH, "wb") as out_f:
            out_f.write(img_data)
        print(f"\nNeutralized 'Before' image saved to {OUTPUT_PATH}")
        print("API Verification Successful!")
    else:
        print("Error: Neutralized image was not in expected data:image/jpeg;base64 format.")

if __name__ == "__main__":
    test_api()
