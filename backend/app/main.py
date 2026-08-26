import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import cv2
import numpy as np
app = FastAPI()
from app.calibration import load_baseline
from app.analyzer import estimate_parameters
from app.neutralizer import neutralize_image, image_to_base64

app = FastAPI(title="ColorGrade Analyzer API")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/status")
def get_status():
    """Checks the baseline calibration status."""
    baseline = load_baseline()
    is_default = baseline.get("mean_L") == 50.0 and baseline.get("cct") == 6500.0
    return {
        "calibrated": not is_default,
        "message": "Running on default baseline" if is_default else "Running on custom calibrated baseline"
    }

@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    """Accepts an image and estimates the Lightroom-style edit parameters."""
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file is not an image.")
        
    try:
        # Read image bytes
        file_bytes = await file.read()
        nparr = np.frombuffer(file_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img_bgr is None:
            raise HTTPException(status_code=400, detail="Invalid or corrupt image file.")
            
        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        
        # Load calibration baseline
        baseline = load_baseline()
        
        # Estimate parameters
        params = estimate_parameters(img_rgb, baseline)
        
        # Generate neutralized "Before" image
        img_neutral = neutralize_image(img_rgb, params)
        neutral_b64 = image_to_base64(img_neutral)
        
        # Return response
        return {
            "success": True,
            "filename": file.filename,
            "parameters": params,
            "neutralized_image": neutral_b64
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal analysis error: {str(e)}")

# Serve static files for frontend production build (if present)
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)