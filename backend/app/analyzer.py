import cv2
import numpy as np
import math

try:
    import colour
    HAS_COLOUR = True
except ImportError:
    HAS_COLOUR = False

def estimate_cct_mccamy(xy):
    """Fallback CCT calculation using McCamy's approximation."""
    x, y = xy[0], xy[1]
    if y == 0 or (0.1858 - y) == 0:
        return 6500.0
    n = (x - 0.3320) / (0.1858 - y)
    cct = 449.0 * (n ** 3) + 3525.0 * (n ** 2) + 6823.3 * n + 5524.31
    return float(cct)

def compute_raw_stats(img_rgb):
    """Computes all raw color and tone metrics for the given RGB image."""
    img_float = img_rgb.astype(np.float32) / 255.0
    
    # Conversions
    img_lab = cv2.cvtColor(img_float, cv2.COLOR_RGB2Lab)
    img_hsv = cv2.cvtColor(img_float, cv2.COLOR_RGB2HSV)
    
    L = img_lab[:, :, 0]   # 0 to 100
    a_channel = img_lab[:, :, 1]   # -127 to 127
    b_channel = img_lab[:, :, 2]   # -127 to 127
    
    H = img_hsv[:, :, 0]   # 0 to 360
    S = img_hsv[:, :, 1]   # 0 to 1
    V = img_hsv[:, :, 2]   # 0 to 1
    
    # Core tone stats (from L channel)
    mean_L = float(np.mean(L))
    std_L = float(np.std(L))
    
    # Percentiles of L
    p1 = float(np.percentile(L, 1))
    p15 = float(np.percentile(L, 15))
    p50 = float(np.percentile(L, 50))
    p90 = float(np.percentile(L, 90))
    p99 = float(np.percentile(L, 99))
    
    # Color Temperature & Tint stats
    mean_a = float(np.mean(a_channel))
    mean_b = float(np.mean(b_channel))
    
    # Estimate CCT and Duv
    mask = (V > 0.05) & (V < 0.95)
    if np.any(mask):
        mean_rgb = np.mean(img_float[mask], axis=0)
    else:
        mean_rgb = np.mean(img_float, axis=(0,1))
        
    cct = 6500.0
    duv = 0.0
    
    if HAS_COLOUR:
        try:
            xyz = colour.sRGB_to_XYZ(mean_rgb)
            xy = colour.XYZ_to_xy(xyz)
            # Ohno 2013 is robust and returns CCT & Duv
            cct_val, duv_val = colour.xy_to_CCT(xy, 'Ohno2013')
            cct = float(cct_val)
            duv = float(duv_val)
        except Exception as e:
            # Fallback to McCamy if Ohno fails
            try:
                xyz = colour.sRGB_to_XYZ(mean_rgb)
                xy = colour.XYZ_to_xy(xyz)
                cct = estimate_cct_mccamy(xy)
            except Exception:
                pass
    else:
        # Simple RGB-based estimation fallback for CCT
        # If blue is higher than red, CCT is higher (cooler).
        # We can map the mean_b axis shift in Lab as a fallback indicator.
        # Reference CCT is 6500K.
        cct = 6500.0 - mean_b * 100.0
        duv = -mean_a / 100.0

    # Saturation & Vibrance
    mean_S = float(np.mean(S))
    # Vibrance is computed as the mean of pixels that have below-average saturation
    low_sat_mask = S < mean_S
    if np.any(low_sat_mask):
        mean_S_low = float(np.mean(S[low_sat_mask]))
    else:
        mean_S_low = mean_S
        
    # Texture, Clarity, Dehaze raw indicators
    # Texture: High frequency contrast. Variance of Laplacian of L
    laplacian = cv2.Laplacian(L, cv2.CV_32F)
    texture_val = float(np.var(laplacian))
    
    # Clarity: Midtone contrast. Variance of L in the midtone range [20, 80]
    midtone_mask = (L >= 20.0) & (L <= 80.0)
    if np.any(midtone_mask):
        clarity_val = float(np.var(L[midtone_mask]))
    else:
        clarity_val = float(np.var(L))
        
    # Dehaze: Dark Channel Prior (DCP)
    min_rgb = np.min(img_float, axis=2)
    dark_channel_mean = float(np.mean(min_rgb))
    
    # 8-Band HSL: red, orange, yellow, green, aqua, blue, purple, magenta
    # Hue ranges (0 to 360)
    bands = {
        "red": ((345, 360), (0, 15)),
        "orange": ((15, 45),),
        "yellow": ((45, 75),),
        "green": ((75, 140),),
        "aqua": ((140, 200),),
        "blue": ((200, 260),),
        "purple": ((260, 310),),
        "magenta": ((310, 345),)
    }
    
    hsl_bands = {}
    for band_name, ranges in bands.items():
        mask = np.zeros_like(H, dtype=bool)
        for r in ranges:
            mask = mask | ((H >= r[0]) & (H < r[1]))
            
        if np.any(mask):
            band_h = H[mask]
            band_s = S[mask]
            band_l = L[mask]
            
            if band_name == "red":
                band_h = np.where(band_h > 300, band_h - 360, band_h)
                
            mean_h = float(np.mean(band_h))
            if band_name == "red" and mean_h < 0:
                mean_h += 360
                
            hsl_bands[band_name] = {
                "hue": mean_h,
                "saturation": float(np.mean(band_s)),
                "luminance": float(np.mean(band_l))
            }
        else:
            centers = {
                "red": 0.0, "orange": 30.0, "yellow": 60.0, "green": 105.0,
                "aqua": 170.0, "blue": 230.0, "purple": 285.0, "magenta": 327.5
            }
            hsl_bands[band_name] = {
                "hue": centers[band_name],
                "saturation": 0.15,
                "luminance": 50.0
            }
            
    # Three-way Color Grading: shadows, midtones, highlights
    chroma = np.sqrt(a_channel**2 + b_channel**2)
    zones = {
        "shadows": L < 33.0,
        "midtones": (L >= 33.0) & (L <= 66.0),
        "highlights": L > 66.0
    }
    
    grading = {}
    for zone_name, z_mask in zones.items():
        if np.any(z_mask):
            z_h = H[z_mask]
            z_chroma = chroma[z_mask]
            
            # Mean angle in polar coordinates
            h_rad = np.deg2rad(z_h)
            mean_cos = np.mean(np.cos(h_rad))
            mean_sin = np.mean(np.sin(h_rad))
            mean_h_deg = float(np.rad2deg(np.arctan2(mean_sin, mean_cos))) % 360.0
            
            grading[zone_name] = {
                "hue": mean_h_deg,
                "saturation": float(np.mean(z_chroma))
            }
        else:
            grading[zone_name] = {
                "hue": 0.0,
                "saturation": 0.0
            }
            
    return {
        "mean_L": mean_L,
        "std_L": std_L,
        "p1": p1,
        "p15": p15,
        "p50": p50,
        "p90": p90,
        "p99": p99,
        "mean_a": mean_a,
        "mean_b": mean_b,
        "cct": cct,
        "duv": duv,
        "mean_S": mean_S,
        "mean_S_low": mean_S_low,
        "texture_val": texture_val,
        "clarity_val": clarity_val,
        "dark_channel_mean": dark_channel_mean,
        "hsl_bands": hsl_bands,
        "grading": grading
    }

def estimate_parameters(img_rgb, baseline):
    """Estimates tone, HSL, and color grading parameters relative to baseline."""
    tgt = compute_raw_stats(img_rgb)
    ref = baseline
    
    # 1. Exposure (scale: -100 to 100)
    # L ranges from 0-100. A difference of 25 is huge. Let's map delta L of 20 to 100.
    delta_L = tgt["mean_L"] - ref["mean_L"]
    exposure = np.clip(delta_L * 5.0, -100.0, 100.0)
    
    # 2. Contrast
    # Ratio of std dev of L. Log2 difference of 1.0 (doubling/halving) -> 100
    if ref["std_L"] > 0 and tgt["std_L"] > 0:
        ratio_std = tgt["std_L"] / ref["std_L"]
        contrast = np.clip(np.log2(ratio_std) * 100.0, -100.0, 100.0)
    else:
        contrast = 0.0
        
    # 3. Highlights (P90)
    delta_p90 = tgt["p90"] - ref["p90"]
    highlights = np.clip(delta_p90 * 5.0, -100.0, 100.0)
    
    # 4. Shadows (P15)
    delta_p15 = tgt["p15"] - ref["p15"]
    shadows = np.clip(delta_p15 * 5.0, -100.0, 100.0)
    
    # 5. Whites (P99)
    delta_p99 = tgt["p99"] - ref["p99"]
    whites = np.clip(delta_p99 * 5.0, -100.0, 100.0)
    
    # 6. Blacks (P1)
    delta_p1 = tgt["p1"] - ref["p1"]
    blacks = np.clip(delta_p1 * 5.0, -100.0, 100.0)
    
    # 7. Temperature (yellow vs blue -> b* in Lab)
    # Target warmer -> higher b* than baseline -> positive slider.
    delta_b = tgt["mean_b"] - ref["mean_b"]
    temperature = np.clip(delta_b * 6.0, -100.0, 100.0)
    
    # 8. Tint (magenta vs green -> a* in Lab)
    # Target more magenta -> higher a* than baseline -> positive slider.
    delta_a = tgt["mean_a"] - ref["mean_a"]
    tint = np.clip(delta_a * 6.0, -100.0, 100.0)
    
    # 9. Saturation
    delta_S = tgt["mean_S"] - ref["mean_S"]
    saturation = np.clip(delta_S * 200.0, -100.0, 100.0)
    
    # 10. Vibrance
    delta_S_low = tgt["mean_S_low"] - ref["mean_S_low"]
    vibrance = np.clip(delta_S_low * 250.0, -100.0, 100.0)
    
    # 11. Texture
    if ref["texture_val"] > 0 and tgt["texture_val"] > 0:
        ratio_tex = tgt["texture_val"] / ref["texture_val"]
        texture = np.clip(np.log10(ratio_tex) * 100.0, -100.0, 100.0)
    else:
        texture = 0.0
        
    # 12. Clarity
    if ref["clarity_val"] > 0 and tgt["clarity_val"] > 0:
        ratio_clar = tgt["clarity_val"] / ref["clarity_val"]
        clarity = np.clip(np.log10(ratio_clar) * 100.0, -100.0, 100.0)
    else:
        clarity = 0.0
        
    # 13. Dehaze
    # Dehazing reduces DCP (clears up haze) and increases contrast.
    # If the target has LESS haze (lower DCP), the parameter should be positive.
    delta_dcp = ref["dark_channel_mean"] - tgt["dark_channel_mean"]
    dehaze = np.clip(delta_dcp * 250.0, -100.0, 100.0)
    
    # Round all parameters
    tone_params = {
        "exposure": round(float(exposure), 1),
        "contrast": round(float(contrast)),
        "highlights": round(float(highlights)),
        "shadows": round(float(shadows)),
        "whites": round(float(whites)),
        "blacks": round(float(blacks)),
        "temperature": round(float(temperature)),
        "tint": round(float(tint)),
        "saturation": round(float(saturation)),
        "vibrance": round(float(vibrance)),
        "texture": round(float(texture)),
        "clarity": round(float(clarity)),
        "dehaze": round(float(dehaze))
    }
    
    # 8-Band HSL adjustments
    hsl_params = {}
    for band in ["red", "orange", "yellow", "green", "aqua", "blue", "purple", "magenta"]:
        t_band = tgt["hsl_bands"][band]
        r_band = ref["hsl_bands"][band]
        
        # Hue Shift: Angular difference
        diff_h = t_band["hue"] - r_band["hue"]
        # Wrap diff to [-180, 180]
        diff_h = (diff_h + 180) % 360 - 180
        hue_shift = np.clip(diff_h * 4.0, -100.0, 100.0)
        
        # Saturation Shift
        diff_s = t_band["saturation"] - r_band["saturation"]
        sat_shift = np.clip(diff_s * 250.0, -100.0, 100.0)
        
        # Luminance Shift (using Lab L*)
        diff_l = t_band["luminance"] - r_band["luminance"]
        lum_shift = np.clip(diff_l * 4.0, -100.0, 100.0)
        
        hsl_params[band] = {
            "hue": round(float(hue_shift)),
            "saturation": round(float(sat_shift)),
            "luminance": round(float(lum_shift))
        }
        
    # 3-Way Color Grading Wheels
    # We compute the relative chroma vector between target and baseline
    grading_params = {}
    for zone in ["shadows", "midtones", "highlights"]:
        t_grad = tgt["grading"][zone]
        r_grad = ref["grading"][zone]
        
        # Convert polar to Cartesian vector (S, H)
        t_x = t_grad["saturation"] * math.cos(math.radians(t_grad["hue"]))
        t_y = t_grad["saturation"] * math.sin(math.radians(t_grad["hue"]))
        
        r_x = r_grad["saturation"] * math.cos(math.radians(r_grad["hue"]))
        r_y = r_grad["saturation"] * math.sin(math.radians(r_grad["hue"]))
        
        # Vector subtraction gives the color grade shift vector
        d_x = t_x - r_x
        d_y = t_y - r_y
        
        shift_sat = math.sqrt(d_x**2 + d_y**2)
        shift_hue = math.degrees(math.atan2(d_y, d_x)) % 360.0
        
        # Scale shift saturation: chroma in Lab of 20 is heavily saturated.
        # Let's map a chroma difference of 20 to 100% saturation on the wheel.
        wheel_sat = np.clip(shift_sat * 5.0, 0.0, 100.0)
        
        # If saturation is extremely low (almost 0), snap hue to 0
        if wheel_sat < 1.0:
            shift_hue = 0.0
            wheel_sat = 0.0
            
        grading_params[zone] = {
            "hue": round(float(shift_hue)),
            "saturation": round(float(wheel_sat))
        }
        
    return {
        "tone": tone_params,
        "hsl": hsl_params,
        "grading": grading_params
    }
