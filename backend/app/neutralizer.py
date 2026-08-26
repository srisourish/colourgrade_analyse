import cv2
import numpy as np
import math
import base64

def neutralize_image(img_rgb, params):
    """Applies the inverse of the estimated parameters to neutralize the color grade."""
    # Scale image to 0-1 float32
    img_float = img_rgb.astype(np.float32) / 255.0
    
    # 1. Convert to CIE Lab to adjust Exposure, Contrast, Temp, Tint, and Color Wheels
    img_lab = cv2.cvtColor(img_float, cv2.COLOR_RGB2Lab)
    L = img_lab[:, :, 0]   # 0 to 100
    a = img_lab[:, :, 1]   # -127 to 127
    b = img_lab[:, :, 2]   # -127 to 127
    
    # Extract tone params
    tone = params["tone"]
    exp_val = tone.get("exposure", 0.0)
    contr_val = tone.get("contrast", 0.0)
    temp_val = tone.get("temperature", 0.0)
    tint_val = tone.get("tint", 0.0)
    sat_val = tone.get("saturation", 0.0)
    
    # Extract color wheels
    grading = params["grading"]
    sh_grad = grading.get("shadows", {"hue": 0, "saturation": 0})
    md_grad = grading.get("midtones", {"hue": 0, "saturation": 0})
    hl_grad = grading.get("highlights", {"hue": 0, "saturation": 0})
    
    # --- Reverse Tone & Contrast in L* ---
    # Exposure shift: L_new = L - (exposure_param / 5.0)
    delta_L = exp_val / 5.0
    L_neutral = L - delta_L
    
    # Contrast shift: scale around midpoint 50 using standard dev ratio
    if contr_val != 0.0:
        contr_ratio = 2.0 ** (contr_val / 100.0)
        L_neutral = 50.0 + (L_neutral - 50.0) / contr_ratio
        
    L_neutral = np.clip(L_neutral, 0.0, 100.0)
    
    # --- Reverse Temperature and Tint in a* and b* ---
    # Temp shift: b_new = b - (temp_param / 6.0)
    # Tint shift: a_new = a - (tint_param / 6.0)
    a_neutral = a - (tint_val / 6.0)
    b_neutral = b - (temp_val / 6.0)
    
    # --- Reverse Color Wheels (Shadows/Midtones/Highlights) with soft transitions ---
    # Calculate shift vectors for each zone
    def get_shift_vector(grad):
        h_rad = math.radians(grad["hue"])
        # Saturation of wheel scaled to chroma shift
        chroma_shift = grad["saturation"] / 5.0
        return chroma_shift * math.cos(h_rad), chroma_shift * math.sin(h_rad)
    
    sh_da, sh_db = get_shift_vector(sh_grad)
    md_da, md_db = get_shift_vector(md_grad)
    hl_da, hl_db = get_shift_vector(hl_grad)
    
    # Compute soft weights based on L_neutral
    # Shadows: 1.0 at L<=20, 0.0 at L>=45
    w_sh = np.clip((45.0 - L_neutral) / 25.0, 0.0, 1.0)
    
    # Highlights: 1.0 at L>=80, 0.0 at L<=55
    w_hl = np.clip((L_neutral - 55.0) / 25.0, 0.0, 1.0)
    
    # Midtones: the remainder
    w_md = 1.0 - w_sh - w_hl
    
    # Apply inverse shift
    a_neutral = a_neutral - (w_sh * sh_da + w_md * md_da + w_hl * hl_da)
    b_neutral = b_neutral - (w_sh * sh_db + w_md * md_db + w_hl * hl_db)
    
    # Clip a* and b* to valid Lab ranges
    a_neutral = np.clip(a_neutral, -127.0, 127.0)
    b_neutral = np.clip(b_neutral, -127.0, 127.0)
    
    # Reassemble Lab and convert back to RGB
    img_lab_neutral = np.stack([L_neutral, a_neutral, b_neutral], axis=2)
    img_rgb_neutral = cv2.cvtColor(img_lab_neutral, cv2.COLOR_Lab2RGB)
    img_rgb_neutral = np.clip(img_rgb_neutral, 0.0, 1.0)
    
    # --- Reverse Saturation in HSV ---
    if sat_val != 0.0:
        img_hsv_neutral = cv2.cvtColor(img_rgb_neutral, cv2.COLOR_RGB2HSV)
        H_ch = img_hsv_neutral[:, :, 0]
        S_ch = img_hsv_neutral[:, :, 1]
        V_ch = img_hsv_neutral[:, :, 2]
        
        # Saturation shift
        delta_S = sat_val / 200.0
        S_neutral = np.clip(S_ch - delta_S, 0.0, 1.0)
        
        img_hsv_neutral = np.stack([H_ch, S_neutral, V_ch], axis=2)
        img_rgb_neutral = cv2.cvtColor(img_hsv_neutral, cv2.COLOR_HSV2RGB)
        img_rgb_neutral = np.clip(img_rgb_neutral, 0.0, 1.0)
        
    # Convert to uint8 RGB
    img_out = (img_rgb_neutral * 255.0).astype(np.uint8)
    return img_out

def image_to_base64(img_rgb):
    """Converts an RGB image to a Base64 JPEG string."""
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    _, buffer = cv2.imencode(".jpg", img_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    b64_str = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/jpeg;base64,{b64_str}"
