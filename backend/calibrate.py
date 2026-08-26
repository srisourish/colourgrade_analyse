import os
import cv2
import numpy as np
import json
import sys

# Add backend directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.calibration import save_baseline, DEFAULT_BASELINE
from app.analyzer import compute_raw_stats

NEUTRAL_REF_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "neutral_references")

def generate_synthetic_references():
    """Generates synthetic neutral images if directory is empty."""
    os.makedirs(NEUTRAL_REF_DIR, exist_ok=True)
    
    # 1. 18% Gray Card
    gray_card = np.full((800, 800, 3), 119, dtype=np.uint8)  # 18% gray is roughly L*=50, which maps to ~119 sRGB
    cv2.imwrite(os.path.join(NEUTRAL_REF_DIR, "synthetic_gray_card.png"), gray_card)
    
    # 2. Smooth Tonal Gradient
    # Ramps from dark gray to bright gray
    ramp = np.zeros((800, 800, 3), dtype=np.uint8)
    for x in range(800):
        val = int(10 + (235 * x / 799))
        ramp[:, x, :] = val
    cv2.imwrite(os.path.join(NEUTRAL_REF_DIR, "synthetic_tonal_ramp.png"), ramp)
    
    # 3. Balanced Color Wheel Grid
    # Generates a grid of 6 primary/secondary colors + 2 grays, all white-balanced.
    grid = np.zeros((800, 800, 3), dtype=np.uint8)
    colors = [
        [200, 50, 50],   # Red
        [50, 200, 50],   # Green
        [50, 50, 200],   # Blue
        [200, 200, 50],  # Yellow
        [50, 200, 200],  # Cyan/Aqua
        [200, 50, 200],  # Magenta
        [220, 220, 220], # Light Gray
        [60, 60, 60]     # Dark Gray
    ]
    # Draw 4x2 grid of color swatches
    swatch_h, swatch_w = 400, 200
    for idx, color in enumerate(colors):
        row = idx // 4
        col = idx % 4
        y_start, y_end = row * swatch_h, (row + 1) * swatch_h
        x_start, x_end = col * swatch_w, (col + 1) * swatch_w
        # Convert RGB to BGR for cv2
        grid[y_start:y_end, x_start:x_end] = [color[2], color[1], color[0]]
        
    cv2.imwrite(os.path.join(NEUTRAL_REF_DIR, "synthetic_color_grid.png"), grid)
    print("Generated 3 synthetic neutral reference images in neutral_references/")

def calibrate():
    """Reads all neutral reference images, computes average stats, and saves baseline."""
    os.makedirs(NEUTRAL_REF_DIR, exist_ok=True)
    
    # Find all images
    valid_exts = (".jpg", ".jpeg", ".png", ".bmp", ".tiff")
    image_files = [f for f in os.listdir(NEUTRAL_REF_DIR) if f.lower().endswith(valid_exts)]
    
    if not image_files:
        print("No neutral reference images found in neutral_references/. Generating synthetic ones...")
        generate_synthetic_references()
        image_files = [f for f in os.listdir(NEUTRAL_REF_DIR) if f.lower().endswith(valid_exts)]
        
    print(f"Starting calibration using {len(image_files)} reference images...")
    
    all_stats = []
    
    for file in image_files:
        path = os.path.join(NEUTRAL_REF_DIR, file)
        try:
            img_bgr = cv2.imread(path)
            if img_bgr is None:
                print(f"Warning: Could not load {file}, skipping.")
                continue
            # Convert to RGB
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            stats = compute_raw_stats(img_rgb)
            all_stats.append(stats)
            print(f"Processed {file} successfully.")
        except Exception as e:
            print(f"Error processing {file}: {e}")
            
    if not all_stats:
        print("Error: No images could be processed. Writing default baseline.")
        save_baseline(DEFAULT_BASELINE)
        return
        
    # Average the stats
    baseline = {}
    
    # Simple float keys
    float_keys = [
        "mean_L", "std_L", "p1", "p15", "p50", "p90", "p99", 
        "mean_a", "mean_b", "cct", "duv", 
        "mean_S", "mean_S_low", "texture_val", "clarity_val", "dark_channel_mean"
    ]
    
    for key in float_keys:
        vals = [s[key] for s in all_stats]
        baseline[key] = float(np.mean(vals))
        
    # Average 8-Band HSL
    baseline["hsl_bands"] = {}
    for band in ["red", "orange", "yellow", "green", "aqua", "blue", "purple", "magenta"]:
        band_hues = []
        band_sats = []
        band_lums = []
        
        for s in all_stats:
            b_data = s["hsl_bands"][band]
            band_hues.append(b_data["hue"])
            band_sats.append(b_data["saturation"])
            band_lums.append(b_data["luminance"])
            
        # Average angles: convert to vectors to avoid boundary wrapping issues
        rads = np.deg2rad(band_hues)
        mean_cos = np.mean(np.cos(rads))
        mean_sin = np.mean(np.sin(rads))
        avg_hue = float(np.rad2deg(np.arctan2(mean_sin, mean_cos))) % 360.0
        
        # Snap avg_hue for red wrap-around if it is close to 360/0
        if band == "red" and avg_hue > 180:
            # Let's adjust so it maps cleanly
            pass
            
        baseline["hsl_bands"][band] = {
            "hue": avg_hue,
            "saturation": float(np.mean(band_sats)),
            "luminance": float(np.mean(band_lums))
        }
        
    # Average Three-Way Color Grading
    baseline["grading"] = {}
    for zone in ["shadows", "midtones", "highlights"]:
        zone_hues = []
        zone_sats = []
        
        for s in all_stats:
            g_data = s["grading"][zone]
            zone_hues.append(g_data["hue"])
            zone_sats.append(g_data["saturation"])
            
        rads = np.deg2rad(zone_hues)
        mean_cos = np.mean(np.cos(rads))
        mean_sin = np.mean(np.sin(rads))
        avg_hue = float(np.rad2deg(np.arctan2(mean_sin, mean_cos))) % 360.0
        
        baseline["grading"][zone] = {
            "hue": avg_hue,
            "saturation": float(np.mean(zone_sats))
        }
        
    # Save to file
    if save_baseline(baseline):
        print(f"Calibration completed! Baseline saved to baseline.json")
    else:
        print("Error saving baseline.json")

if __name__ == "__main__":
    calibrate()
