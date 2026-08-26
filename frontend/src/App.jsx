import React, { useState, useEffect, useRef } from 'react';
import {
  UploadCloud,
  SlidersHorizontal,
  Sparkles,
  RefreshCw,
  Eye,
  AlertCircle,
  Info
} from 'lucide-react';

// API base URL
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function App() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const [sliderPos, setSliderPos] = useState(50);
  const sliderContainerRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  const [activeTab, setActiveTab] = useState('tone');

  const [histData, setHistData] = useState(null);
  const histogramCanvasRef = useRef(null);
  const imageRef = useRef(null);

  // ---------------------------------------
  // Cleanup preview URL
  // ---------------------------------------
  useEffect(() => {
    return () => {
      if (previewUrl && previewUrl.startsWith('blob:')) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  // ---------------------------------------
  // Draw histogram
  // ---------------------------------------
  useEffect(() => {
    if (histData && histogramCanvasRef.current) {
      drawHistogram(histogramCanvasRef.current, histData);
    }
  }, [histData]);

  // ---------------------------------------
  // Drag & Drop
  // ---------------------------------------
  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e) => {
    e.preventDefault();

    const droppedFile = e.dataTransfer.files[0];

    if (droppedFile && droppedFile.type.startsWith('image/')) {
      processFile(droppedFile);
    } else {
      setError('Please drop an image file (PNG, JPG, JPEG).');
    }
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];

    if (selectedFile) {
      processFile(selectedFile);
    }
  };

  // ---------------------------------------
  // Process selected image
  // ---------------------------------------
  const processFile = (selectedFile) => {
    setError(null);
    setFile(selectedFile);

    const objectUrl = URL.createObjectURL(selectedFile);

    setPreviewUrl(objectUrl);
    setResults(null);
    setHistData(null);
  };

  // ---------------------------------------
  // Image loaded
  // ---------------------------------------
  const handleImageLoaded = () => {
    if (!imageRef.current) return;

    try {
      const hData = calculateHistogram(imageRef.current);
      setHistData(hData);
    } catch (err) {
      console.error(
        'Failed to calculate histogram in browser:',
        err
      );
    }
  };

  // =======================================
  // IMPORTANT: ANALYZE IMAGE
  // =======================================
  const analyzeImage = async () => {
    if (!file) {
      setError('Please select an image first.');
      return;
    }

    setAnalyzing(true);
    setError(null);

    try {
      // Create multipart form
      const formData = new FormData();

      // IMPORTANT:
      // FastAPI expects parameter name "file"
      formData.append('file', file);

      console.log('Sending image to:', `${API_URL}/analyze`);
      console.log('File:', file.name);

      const response = await fetch(`${API_URL}/analyze`, {
        method: 'POST',
        body: formData,
      });

      console.log('HTTP status:', response.status);

      // Read response ONLY ONCE
      const responseText = await response.text();

      console.log('Raw API response:', responseText);

      // Handle HTTP errors
      if (!response.ok) {
        let errorMessage = `API error ${response.status}`;

        try {
          const errorData = JSON.parse(responseText);

          if (errorData.detail) {
            errorMessage = errorData.detail;
          }
        } catch {
          if (responseText) {
            errorMessage = responseText;
          }
        }

        throw new Error(errorMessage);
      }

      // Make sure backend actually returned something
      if (!responseText.trim()) {
        throw new Error(
          'The server returned an empty response.'
        );
      }

      // Convert response to JSON
      let data;

      try {
        data = JSON.parse(responseText);
      } catch (jsonError) {
        console.error(
          'Invalid JSON returned by API:',
          responseText
        );

        throw new Error(
          'The server returned an invalid JSON response.'
        );
      }

      console.log('Analysis result:', data);

      // Check success flag
      if (data.success) {
        setResults(data);
      } else {
        throw new Error(
          data.detail || 'Analysis failed.'
        );
      }

    } catch (err) {
      console.error('Analysis error:', err);

      setError(
        err.message ||
        'An error occurred while analyzing the image.'
      );
    } finally {
      setAnalyzing(false);
    }
  };

  // ---------------------------------------
  // Reset
  // ---------------------------------------
  const resetApp = () => {
    if (previewUrl && previewUrl.startsWith('blob:')) {
      URL.revokeObjectURL(previewUrl);
    }

    setFile(null);
    setPreviewUrl(null);
    setResults(null);
    setError(null);
    setHistData(null);
    setSliderPos(50);
  };

  // ---------------------------------------
  // Before / After slider
  // ---------------------------------------
  const handleSliderMove = (clientX) => {
    if (!sliderContainerRef.current) return;

    const rect =
      sliderContainerRef.current.getBoundingClientRect();

    const x = clientX - rect.left;

    const percentage = Math.max(
      0,
      Math.min(100, (x / rect.width) * 100)
    );

    setSliderPos(percentage);
  };

  const handleMouseDown = (e) => {
    setIsDragging(true);
    handleSliderMove(e.clientX);
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;

    handleSliderMove(e.clientX);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleTouchMove = (e) => {
    if (e.touches.length > 0) {
      handleSliderMove(e.touches[0].clientX);
    }
  };

  // ---------------------------------------
  // Histogram calculation
  // ---------------------------------------
  const calculateHistogram = (imgElement) => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    const size = 150;

    canvas.width = size;
    canvas.height = size;

    ctx.drawImage(
      imgElement,
      0,
      0,
      size,
      size
    );

    const imgData = ctx.getImageData(
      0,
      0,
      size,
      size
    );

    const data = imgData.data;

    const rHist = new Array(256).fill(0);
    const gHist = new Array(256).fill(0);
    const bHist = new Array(256).fill(0);
    const lHist = new Array(256).fill(0);

    for (let i = 0; i < data.length; i += 4) {
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];

      const l = Math.round(
        0.299 * r +
        0.587 * g +
        0.114 * b
      );

      rHist[r]++;
      gHist[g]++;
      bHist[b]++;
      lHist[l]++;
    }

    return {
      r: rHist,
      g: gHist,
      b: bHist,
      l: lHist,
    };
  };

  // ---------------------------------------
  // Draw histogram
  // ---------------------------------------
  const drawHistogram = (canvas, histData) => {
    const ctx = canvas.getContext('2d');

    const width = canvas.width = canvas.offsetWidth;
    const height = canvas.height = canvas.offsetHeight;

    ctx.clearRect(
      0,
      0,
      width,
      height
    );

    const maxVal = Math.max(
      Math.max(...histData.r),
      Math.max(...histData.g),
      Math.max(...histData.b),
      Math.max(...histData.l)
    );

    if (maxVal === 0) return;

    const drawChannel = (
      hist,
      color,
      fillOpacity
    ) => {
      ctx.beginPath();

      ctx.moveTo(
        0,
        height
      );

      for (let i = 0; i < 256; i++) {
        const x =
          (i / 255) * width;

        const y =
          height -
          (hist[i] / maxVal) *
          (height - 8);

        ctx.lineTo(x, y);
      }

      ctx.lineTo(
        width,
        height
      );

      ctx.closePath();

      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;

      ctx.stroke();

      if (fillOpacity) {
        ctx.fillStyle = fillOpacity;
        ctx.fill();
      }
    };

    drawChannel(
      histData.r,
      'rgba(239, 68, 68, 0.75)',
      'rgba(239, 68, 68, 0.08)'
    );

    drawChannel(
      histData.g,
      'rgba(34, 197, 94, 0.75)',
      'rgba(34, 197, 94, 0.08)'
    );

    drawChannel(
      histData.b,
      'rgba(59, 130, 246, 0.75)',
      'rgba(59, 130, 246, 0.08)'
    );

    drawChannel(
      histData.l,
      'rgba(255, 255, 255, 0.35)',
      'rgba(255, 255, 255, 0.03)'
    );
  };

  // ---------------------------------------
  // Color wheel position
  // ---------------------------------------
  const getGradingWheelDotPosition = (
    hue,
    saturation
  ) => {
    const radiusBound = 46;
    const center = 60;

    const r =
      (saturation / 100) *
      radiusBound;

    const hueRad =
      (hue * Math.PI) / 180;

    const x =
      center +
      r * Math.sin(hueRad);

    const y =
      center -
      r * Math.cos(hueRad);

    return {
      x,
      y
    };
  };

  // ---------------------------------------
  // Slider component
  // ---------------------------------------
  const renderSlider = (
    label,
    value,
    min,
    max,
    unit = '',
    className = ''
  ) => {
    let valueColorClass = 'neutral';

    if (value > 0) {
      valueColorClass = 'positive';
    } else if (value < 0) {
      valueColorClass = 'negative';
    }

    const displayVal =
      value > 0
        ? `+${value}`
        : value;

    return (
      <div className="slider-row">

        <div className="slider-header">

          <span className="slider-label">
            {label}
          </span>

          <span
            className={`slider-value ${valueColorClass}`}
          >
            {displayVal}
            {unit}
          </span>

        </div>

        <input
          type="range"
          min={min}
          max={max}
          value={value}
          className={`custom-range ${className}`}
          disabled
        />

      </div>
    );
  };

  // =======================================
  // UI
  // =======================================

  return (
    <div
      className="app-container"
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onTouchEnd={handleMouseUp}
    >

      {/* HEADER */}
      <header className="app-header">

        <div className="app-title-group">

          <div className="app-logo">
            <SlidersHorizontal
              size={22}
              color="#fff"
            />
          </div>

          <div>

            <h1 className="app-title">
              ColorGrade Analyzer
            </h1>

            <p
              style={{
                fontSize: '0.8rem',
                color: 'var(--text-secondary)'
              }}
            >
              Lightroom Look Parameter Estimator
            </p>

          </div>

        </div>

        {previewUrl && (
          <button
            onClick={resetApp}
            className="glass-panel"
            style={{
              padding: '0.5rem 1rem',
              border:
                '1px solid rgba(255,255,255,0.1)',
              borderRadius: '8px',
              color: '#fff',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontWeight: 600,
              fontSize: '0.85rem'
            }}
          >

            <RefreshCw size={14} />

            Reset

          </button>
        )}

      </header>

      {/* ERROR */}
      {error && (
        <div
          className="glass-panel"
          style={{
            padding: '1rem',
            border:
              '1px solid rgba(239, 68, 68, 0.2)',
            background:
              'rgba(239, 68, 68, 0.1)',
            borderRadius: '12px',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            color: '#fca5a5'
          }}
        >

          <AlertCircle size={20} />

          <span>
            {error}
          </span>

        </div>
      )}

      {/* UPLOAD SCREEN */}
      {!previewUrl ? (

        <main
          className="glass-panel"
          style={{
            padding: '3rem 2rem',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >

          <div
            className="dropzone"
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onClick={() =>
              document
                .getElementById('image-upload')
                .click()
            }
            style={{
              width: '100%',
              maxWidth: '600px'
            }}
          >

            <UploadCloud
              size={48}
              color="var(--accent-color)"
              style={{
                marginBottom: '1rem'
              }}
            />

            <h2
              style={{
                fontSize: '1.25rem',
                marginBottom: '0.5rem'
              }}
            >
              Upload Color Graded Image
            </h2>

            <p
              style={{
                color:
                  'var(--text-secondary)',
                fontSize: '0.9rem',
                marginBottom: '1.5rem'
              }}
            >
              Drag and drop your graded image
              here, or click to browse.
            </p>

            <span
              style={{
                fontSize: '0.75rem',
                color:
                  'var(--text-muted)'
              }}
            >
              Supports JPG, JPEG, PNG, BMP
            </span>

            <input
              type="file"
              id="image-upload"
              accept="image/*"
              onChange={handleFileChange}
              style={{
                display: 'none'
              }}
            />

          </div>

        </main>

      ) : (

        <main className="dashboard-grid">

          {/* LEFT PANEL */}
          <section
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '1.5rem'
            }}
          >

            {/* IMAGE */}
            <div
              className="glass-panel"
              style={{
                padding: '1rem',
                position: 'relative'
              }}
            >

              <h3
                style={{
                  fontSize: '1rem',
                  color:
                    'var(--text-secondary)',
                  marginBottom: '0.75rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}
              >

                <Eye size={16} />

                Look Comparison

              </h3>

              <div
                className="slider-container"
                ref={sliderContainerRef}
                onMouseDown={handleMouseDown}
                onTouchStart={handleMouseDown}
                onTouchMove={handleTouchMove}
              >

                {results ? (

                  <>

                    {/* BEFORE */}
                    <img
                      src={
                        results.neutralized_image
                      }
                      alt="Before Neutralized"
                      className="slider-image slider-before"
                      style={{
                        clipPath:
                          `polygon(0 0, ${sliderPos}% 0, ${sliderPos}% 100%, 0 100%)`
                      }}
                    />

                    {/* AFTER */}
                    <img
                      src={previewUrl}
                      alt="After Graded"
                      className="slider-image slider-after"
                    />

                    {/* HANDLE */}
                    <div
                      className="slider-handle"
                      style={{
                        left:
                          `${sliderPos}%`
                      }}
                    >

                      <div className="slider-handle-button">

                        <span
                          style={{
                            fontSize: '12px',
                            fontWeight: 'bold',
                            color:
                              'var(--text-muted)'
                          }}
                        >
                          ↔
                        </span>

                      </div>

                    </div>

                    {/* LABELS */}
                    <span
                      style={{
                        position: 'absolute',
                        bottom: '12px',
                        left: '12px',
                        zIndex: 30,
                        background:
                          'rgba(0,0,0,0.6)',
                        padding:
                          '0.25rem 0.5rem',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        color: '#9ca3af',
                        pointerEvents: 'none'
                      }}
                    >
                      Before (Neutralized)
                    </span>

                    <span
                      style={{
                        position: 'absolute',
                        bottom: '12px',
                        right: '12px',
                        zIndex: 30,
                        background:
                          'rgba(0,0,0,0.6)',
                        padding:
                          '0.25rem 0.5rem',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        color: '#3b82f6',
                        pointerEvents: 'none'
                      }}
                    >
                      After (Graded)
                    </span>

                  </>

                ) : (

                  <>

                    <img
                      src={previewUrl}
                      ref={imageRef}
                      onLoad={handleImageLoaded}
                      alt="Uploaded Graded"
                      className="slider-image"
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'contain'
                      }}
                    />

                    {!analyzing && (

                      <div
                        style={{
                          position: 'absolute',
                          inset: 0,
                          background:
                            'rgba(0,0,0,0.4)',
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          justifyContent: 'center',
                          padding: '1rem',
                          zIndex: 30
                        }}
                      >

                        <button
                          onClick={analyzeImage}
                          className="glass-panel pulsate"
                          style={{
                            padding:
                              '0.75rem 1.5rem',
                            background:
                              'var(--accent-color)',
                            border: 'none',
                            borderRadius: '8px',
                            color: '#fff',
                            fontSize: '0.95rem',
                            fontWeight: 700,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem'
                          }}
                        >

                          <Sparkles size={16} />

                          Estimate Color Grade

                        </button>

                      </div>

                    )}

                  </>

                )}

                {/* ANALYZING */}
                {analyzing && (

                  <div
                    style={{
                      position: 'absolute',
                      inset: 0,
                      background:
                        'rgba(0,0,0,0.7)',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '1rem',
                      zIndex: 40
                    }}
                  >

                    <RefreshCw
                      className="pulsate"
                      size={32}
                      color="var(--accent-color)"
                      style={{
                        animation:
                          'spin 2s linear infinite'
                      }}
                    />

                    <span
                      style={{
                        fontWeight: 600,
                        fontSize: '0.95rem'
                      }}
                    >
                      Analyzing Image Color Grade...
                    </span>

                  </div>

                )}

              </div>

            </div>

            {/* HISTOGRAM */}
            <div
              className="glass-panel"
              style={{
                padding: '1rem'
              }}
            >

              <h3
                style={{
                  fontSize: '1rem',
                  color:
                    'var(--text-secondary)',
                  marginBottom: '0.75rem'
                }}
              >
                Live Image Histogram
              </h3>

              <div className="histogram-container">

                {histData ? (

                  <canvas
                    ref={histogramCanvasRef}
                    className="histogram-canvas"
                  />

                ) : (

                  <div
                    style={{
                      width: '100%',
                      height: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color:
                        'var(--text-muted)',
                      fontSize: '0.8rem'
                    }}
                  >
                    Loading histogram...
                  </div>

                )}

              </div>

              <div
                style={{
                  display: 'flex',
                  gap: '1rem',
                  justifyContent: 'center',
                  marginTop: '0.5rem',
                  fontSize: '0.75rem'
                }}
              >

                <span>🔴 Red</span>
                <span>🟢 Green</span>
                <span>🔵 Blue</span>
                <span>⚪ Luminance</span>

              </div>

            </div>

          </section>

          {/* RIGHT PANEL */}
          <section
            className="glass-panel"
            style={{
              padding: '1.5rem',
              display: 'flex',
              flexDirection: 'column'
            }}
          >

            {/* TABS */}
            <div className="panel-tabs">

              <button
                className={`panel-tab ${
                  activeTab === 'tone'
                    ? 'active'
                    : ''
                }`}
                onClick={() =>
                  setActiveTab('tone')
                }
              >
                Tone & Presence
              </button>

              <button
                className={`panel-tab ${
                  activeTab === 'hsl'
                    ? 'active'
                    : ''
                }`}
                onClick={() =>
                  setActiveTab('hsl')
                }
              >
                8-Band HSL
              </button>

              <button
                className={`panel-tab ${
                  activeTab === 'wheels'
                    ? 'active'
                    : ''
                }`}
                onClick={() =>
                  setActiveTab('wheels')
                }
              >
                Color Wheels
              </button>

            </div>

            {/* RESULTS */}
            {results ? (

              <div
                style={{
                  flex: 1,
                  overflowY: 'auto',
                  maxHeight:
                    'calc(100vh - 220px)',
                  paddingRight:
                    '0.25rem'
                }}
              >

                {/* TONE */}
                {activeTab === 'tone' && (

                  <div>

                    <h4>
                      Basic Tone Controls
                    </h4>

                    {renderSlider(
                      'Exposure',
                      results.parameters.tone.exposure,
                      -4,
                      4,
                      ' eV'
                    )}

                    {renderSlider(
                      'Contrast',
                      results.parameters.tone.contrast,
                      -100,
                      100
                    )}

                    {renderSlider(
                      'Highlights',
                      results.parameters.tone.highlights,
                      -100,
                      100
                    )}

                    {renderSlider(
                      'Shadows',
                      results.parameters.tone.shadows,
                      -100,
                      100
                    )}

                    {renderSlider(
                      'Whites',
                      results.parameters.tone.whites,
                      -100,
                      100
                    )}

                    {renderSlider(
                      'Blacks',
                      results.parameters.tone.blacks,
                      -100,
                      100
                    )}

                    <h4>
                      White Balance
                    </h4>

                    {renderSlider(
                      'Temperature',
                      results.parameters.tone.temperature,
                      -100,
                      100
                    )}

                    {renderSlider(
                      'Tint',
                      results.parameters.tone.tint,
                      -100,
                      100
                    )}

                    <h4>
                      Presence & Details
                    </h4>

                    {renderSlider(
                      'Vibrance',
                      results.parameters.tone.vibrance,
                      -100,
                      100
                    )}

                    {renderSlider(
                      'Saturation',
                      results.parameters.tone.saturation,
                      -100,
                      100
                    )}

                    {renderSlider(
                      'Texture',
                      results.parameters.tone.texture,
                      -100,
                      100
                    )}

                    {renderSlider(
                      'Clarity',
                      results.parameters.tone.clarity,
                      -100,
                      100
                    )}

                    {renderSlider(
                      'Dehaze',
                      results.parameters.tone.dehaze,
                      -100,
                      100
                    )}

                  </div>
                )}

                {/* HSL */}
                {activeTab === 'hsl' && (

                  <div>

                    <h4>
                      8-Band HSL Shifts
                    </h4>

                    <p
                      style={{
                        fontSize: '0.75rem',
                        color:
                          'var(--text-muted)',
                        marginBottom:
                          '1.25rem'
                      }}
                    >
                      Estimated Hue,
                      Saturation and
                      Luminance changes.
                    </p>

                    <div className="hsl-grid">

                      {Object.keys(
                        results.parameters.hsl
                      ).map((band) => {

                        const p =
                          results.parameters
                            .hsl[band];

                        return (

                          <div
                            key={band}
                            className="hsl-card"
                          >

                            <span className="hsl-band-name">
                              {band}
                            </span>

                            <div className="hsl-metric">
                              <span>H</span>
                              <span>
                                {p.hue > 0
                                  ? `+${p.hue}`
                                  : p.hue}
                              </span>
                            </div>

                            <div className="hsl-metric">
                              <span>S</span>
                              <span>
                                {p.saturation > 0
                                  ? `+${p.saturation}`
                                  : p.saturation}
                              </span>
                            </div>

                            <div className="hsl-metric">
                              <span>L</span>
                              <span>
                                {p.luminance > 0
                                  ? `+${p.luminance}`
                                  : p.luminance}
                              </span>
                            </div>

                          </div>

                        );
                      })}

                    </div>

                  </div>
                )}

                {/* WHEELS */}
                {activeTab === 'wheels' && (

                  <div>

                    <h4>
                      Three-Way Color Grading
                    </h4>

                    <p
                      style={{
                        fontSize: '0.75rem',
                        color:
                          'var(--text-muted)',
                        marginBottom:
                          '1.5rem'
                      }}
                    >
                      Estimated color
                      coordinates for
                      Shadows, Midtones
                      and Highlights.
                    </p>

                    <div className="wheels-container">

                      {[
                        'shadows',
                        'midtones',
                        'highlights'
                      ].map((zone) => {

                        const wheelData =
                          results
                            .parameters
                            .grading[zone];

                        const pos =
                          getGradingWheelDotPosition(
                            wheelData.hue,
                            wheelData.saturation
                          );

                        return (

                          <div
                            key={zone}
                            className="wheel-card"
                          >

                            <span className="wheel-title">
                              {zone}
                            </span>

                            <div
                              style={{
                                position:
                                  'relative',
                                width: '120px',
                                height: '120px',
                                borderRadius:
                                  '50%',
                                background:
                                  'radial-gradient(circle, rgba(15,17,26,.92) 0%, rgba(15,17,26,.2) 65%, transparent 100%), conic-gradient(red, yellow, lime, cyan, blue, magenta, red)',
                                border:
                                  '1px solid rgba(255,255,255,.1)'
                              }}
                            >

                              <div
                                style={{
                                  position:
                                    'absolute',
                                  left:
                                    `${pos.x}px`,
                                  top:
                                    `${pos.y}px`,
                                  transform:
                                    'translate(-50%, -50%)',
                                  width: '10px',
                                  height: '10px',
                                  borderRadius:
                                    '50%',
                                  background:
                                    '#fff',
                                  border:
                                    '1.5px solid #000',
                                  boxShadow:
                                    '0 0 8px #fff'
                                }}
                              />

                            </div>

                            <div
                              style={{
                                marginTop:
                                  '0.25rem',
                                fontSize:
                                  '0.75rem'
                              }}
                            >

                              H:{' '}
                              <b>
                                {wheelData.hue}°
                              </b>

                              <br />

                              S:{' '}
                              <b>
                                {wheelData.saturation}%
                              </b>

                            </div>

                          </div>

                        );
                      })}

                    </div>

                  </div>
                )}

              </div>

            ) : (

              <div
                style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection:
                    'column',
                  alignItems:
                    'center',
                  justifyContent:
                    'center',
                  color:
                    'var(--text-muted)',
                  textAlign: 'center',
                  padding: '2rem'
                }}
              >

                <Info
                  size={32}
                  style={{
                    marginBottom:
                      '0.75rem',
                    opacity: 0.5
                  }}
                />

                <h4
                  style={{
                    color: '#fff',
                    fontSize:
                      '0.95rem',
                    marginBottom:
                      '0.25rem'
                  }}
                >
                  Analysis Needed
                </h4>

                <p
                  style={{
                    fontSize: '0.8rem'
                  }}
                >
                  Click the
                  "Estimate Color Grade"
                  button to calculate
                  the parameters.
                </p>

              </div>

            )}

          </section>

        </main>
      )}

    </div>
  );
}

export default App;