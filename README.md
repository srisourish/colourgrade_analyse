# ColorGrade Analyzer

ColorGrade Analyzer is an application that uses a Python (FastAPI) backend and a React (Vite) frontend to take an uploaded color-graded image and estimate the Lightroom/Camera Raw-style edit parameters (exposure, contrast, temperature, tint, HSL band shifts, color grading wheels, etc.) that would produce that look. 

Since no original image is available, the backend also computes the **inverse** adjustments and applies them to generate a "neutralized" (Before) version of the image, allowing for a live before/after slider comparison.

---

## Features
1. **Tone Parameter Estimation**: Estimates Exposure, Contrast, Highlights, Shadows, Whites, Blacks, Temp, Tint, Saturation, Vibrance, Texture, Clarity, and Dehaze, mapped to standard `-100` to `+100` scales.
2. **8-Band HSL Breakdown**: Analyzes Red, Orange, Yellow, Green, Aqua, Blue, Purple, and Magenta bands, computing hue-shift, saturation, and luminance shifts.
3. **Three-Way Color Wheels**: Groups pixels into Shadows, Midtones, and Highlights to calculate relative color cast vectors, representing the grading wheels.
4. **Before/After Split Slider**: Interactive comparison slider between the original image and the neutralized version.
5. **Live Canvas Histogram**: Multi-channel overlay (Red, Green, Blue, and Luminance) calculated dynamically in the browser.
6. **Calibration Tool**: Command-line script to generate custom neutral references and calculate a baseline.

---

## Directory Structure

```
colourgrade_analyser/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI Server entry point
│   │   ├── analyzer.py      # Core image analytics pipeline
│   │   ├── neutralizer.py   # Inverse-grade image generator
│   │   └── calibration.py   # Baseline JSON management
│   ├── neutral_references/  # Folder for neutral reference calibration images
│   ├── baseline.json        # Calibrated baseline metrics
│   ├── calibrate.py         # CLI calibration script
│   └── test_analyze.py      # Automated API verification test
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main React Application
│   │   ├── index.css        # CSS variable theme & styling
│   │   └── main.jsx         # React DOM root entry
│   ├── package.json
│   └── vite.config.js
├── sample_graded.png        # Test graded image (Teal & Orange sunset)
├── neutralized_preview.jpg  # Neutralized output preview from API test
└── README.md
```

---

## Setup & Running Instructions

### 1. Backend Setup & Run

Navigate to the `backend` folder and run the FastAPI server:

```bash
cd backend
# Run server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
The backend API documentation will be available at `http://127.0.0.1:8000/docs`.

### 2. Frontend Setup & Run

Navigate to the `frontend` folder, install packages, and start the Vite dev server:

```bash
cd frontend
npm install
npm run dev
```
The React frontend will be running on `http://localhost:5173/`.

### 3. Calibration

If you want to calibrate against your own set of neutral-reference images:
1. Place your unedited neutral photos (e.g., gray cards, flat light landscapes) inside `backend/neutral_references/`.
2. Run the calibration script from the project root:
   ```bash
   python backend/calibrate.py
   ```
This updates `backend/baseline.json`. If the folder is empty, the script automatically generates synthetic reference images (Gray Card, Tonal Ramp, Color Grid) to calibrate.

---

## Technology Stack
- **Backend**: Python 3.13, FastAPI, OpenCV, NumPy, scikit-image, colour-science.
- **Frontend**: React (Vite template), Lucide React (icons), Vanilla CSS (responsive glassmorphism UI).
