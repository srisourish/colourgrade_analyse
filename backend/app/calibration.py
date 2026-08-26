import os
import json

BASELINE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "baseline.json")

DEFAULT_BASELINE = {
    "mean_L": 50.0,
    "std_L": 20.0,
    "p1": 5.0,
    "p15": 20.0,
    "p50": 50.0,
    "p90": 80.0,
    "p99": 95.0,
    "mean_a": 0.0,
    "mean_b": 0.0,
    "cct": 6500.0,
    "duv": 0.0,
    "mean_S": 0.15,
    "mean_S_low": 0.10,
    "texture_val": 10.0,
    "clarity_val": 400.0,
    "dark_channel_mean": 0.05,
    "hsl_bands": {
        "red": {"hue": 0.0, "saturation": 0.15, "luminance": 50.0},
        "orange": {"hue": 30.0, "saturation": 0.15, "luminance": 50.0},
        "yellow": {"hue": 60.0, "saturation": 0.15, "luminance": 50.0},
        "green": {"hue": 105.0, "saturation": 0.15, "luminance": 50.0},
        "aqua": {"hue": 170.0, "saturation": 0.15, "luminance": 50.0},
        "blue": {"hue": 230.0, "saturation": 0.15, "luminance": 50.0},
        "purple": {"hue": 285.0, "saturation": 0.15, "luminance": 50.0},
        "magenta": {"hue": 327.5, "saturation": 0.15, "luminance": 50.0}
    },
    "grading": {
        "shadows": {"hue": 0.0, "saturation": 0.0},
        "midtones": {"hue": 0.0, "saturation": 0.0},
        "highlights": {"hue": 0.0, "saturation": 0.0}
    }
}

def load_baseline():
    """Loads baseline parameters from file, or returns default baseline if not found."""
    if os.path.exists(BASELINE_PATH):
        try:
            with open(BASELINE_PATH, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading baseline.json: {e}. Using defaults.")
    return DEFAULT_BASELINE

def save_baseline(baseline_data):
    """Saves baseline data to baseline.json."""
    try:
        with open(BASELINE_PATH, "w") as f:
            json.dump(baseline_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving baseline.json: {e}")
        return False
