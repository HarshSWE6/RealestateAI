# 🏠 AI Property Video Generator

**Track:** AI Content Creation / Multimedia  
**Purpose:** Automatically transform property photos and metadata into professional, ready-to-share promotional videos — no video editor needed.

---

## 📋 Overview

Real estate sales teams often have property photos and basic details, but manually creating promotional videos for every listing is time-consuming. This tool automates the entire process:

1. **Input** property details (name, location, price, features) and 4–8 images
2. **Generate** a voiceover script using only the supplied facts
3. **Produce** a polished MP4 video with Ken Burns motion, typography overlays, transitions, narration, and background music
4. **Export** a ready-to-share video in multiple aspect ratios

### 🎯 Key Features

| Feature | Description |
|---|---|
| **AI Voiceover** | Neural text-to-speech narration using Microsoft Edge TTS (with gTTS and pyttsx3 offline fallbacks) |
| **Ken Burns Motion** | Smooth zoom and pan effects on static property images |
| **Smart Scene Layout** | Auto-generates intro, feature, and CTA scenes from property data |
| **Text Overlays** | Professional title cards, badges, captions, and gradient scrims |
| **Cross-Dissolve Transitions** | Smooth blending between scenes |
| **Background Music** | Royalty-free BGM with volume ducking during narration |
| **Multi-Format Export** | 16:9 (YouTube), 9:16 (Reels/Shorts), 1:1 (Social) |
| **Graceful Error Handling** | Missing images or data produce fallback graphics and helpful warnings |
| **Two Interfaces** | Interactive Streamlit web UI + command-line CLI |

---

## 🗂️ Project Structure

```
task/
├── app.py                          # Streamlit web application (form UI)
├── generate_video.py               # CLI orchestrator (main entry point)
├── script_generator.py             # Factual scene & voiceover script generation
├── audio_engine.py                 # TTS synthesis + BGM mixing (FFmpeg)
├── video_renderer.py               # Video rendering pipeline (FFmpeg pipe)
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── sample_data/
│   ├── property_2bhk_bangalore.json  # Sample property JSON input
│   ├── bgm_luxury.wav               # Royalty-free background music
│   └── images/
│       ├── 01_exterior.jpg
│       ├── 02_living_room.jpg
│       ├── 03_kitchen.jpg
│       ├── 04_bedroom.jpg
│       └── 05_amenities.jpg
└── output/                         # Generated videos and temp audio files
    └── sample_property_tour.mp4    # Pre-generated sample output
```

---

## 🚀 Installation & Setup

### Prerequisites

- **Python 3.9+** (tested on Python 3.10)
- **FFmpeg** — installed via `imageio-ffmpeg` (bundled, no separate install needed)
- **Windows** (uses Windows system fonts; Linux/Mac will use fallback fonts)

### Step 1: Clone or Extract the Project

```bash
cd path/to/task
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Verify Installation

```bash
python -c "import cv2, numpy, PIL, edge_tts, imageio_ffmpeg; print('All dependencies OK')"
```

---

## 💻 Usage

### Option A: Web UI (Recommended)

Launch the interactive Streamlit web application:

```bash
streamlit run app.py
```

This opens a browser-based form where you can:
- Enter property details (name, price, location, features)
- Upload 4–8 property photos
- Choose aspect ratio, AI voice, and audio options
- Click **Generate Video** and preview/download the result

### Option B: Command-Line Interface

```bash
# Generate using sample data (default)
python generate_video.py

# Custom property JSON
python generate_video.py --input your_property.json --output output/your_video.mp4

# Vertical video for Instagram Reels
python generate_video.py --input your_property.json --format 9:16

# Different voice
python generate_video.py --input your_property.json --voice en-US-ChristopherNeural

# Disable narration (images + BGM only)
python generate_video.py --no-narration

# Custom BGM
python generate_video.py --bgm path/to/your_bgm.wav
```

**CLI Arguments:**

| Flag | Default | Description |
|---|---|---|
| `--input`, `-i` | `sample_data/property_2bhk_bangalore.json` | Property JSON input file |
| `--output`, `-o` | `output/sample_property_tour.mp4` | Output MP4 file path |
| `--format`, `-f` | `16:9` | Aspect ratio: `16:9`, `9:16`, or `1:1` |
| `--voice`, `-v` | `en-IN-NeerjaNeural` | Edge TTS voice model |
| `--bgm` | `sample_data/bgm_luxury.wav` | Custom BGM audio file |
| `--no-narration` | (flag) | Disable AI voiceover |
| `--no-bgm` | (flag) | Disable background music |

---

## 📄 Input JSON Schema

```json
{
  "property_name": "The Azure Residences",
  "property_type": "2-BHK Ultra Luxury Apartment",
  "location": "Whitefield, Bengaluru",
  "price": "₹1.25 Crore",
  "carpet_area": "1,450 sq.ft.",
  "possession": "Ready to Move",
  "key_features": [
    "Grand architecture with twilight ambient illumination",
    "Expansive living room with Italian marble flooring",
    "Modern modular kitchen with premium quartz island",
    "Spacious master bedroom with panoramic city vistas",
    "World-class rooftop infinity pool and sunset lounge"
  ],
  "contact": {
    "agent_name": "Realty Assistant Concierge",
    "phone": "+91 98765 43210",
    "email": "sales@realtyassistant.in"
  },
  "cta_text": "Book your exclusive private walkthrough today!",
  "images": [
    "sample_data/images/01_exterior.jpg",
    "sample_data/images/02_living_room.jpg",
    "sample_data/images/03_kitchen.jpg",
    "sample_data/images/04_bedroom.jpg",
    "sample_data/images/05_amenities.jpg"
  ],
  "bgm_audio": "sample_data/bgm_luxury.wav"
}
```

All fields except `property_name` and `images` are optional. The system gracefully handles missing data.

---

## 🏗️ Architecture & Approach

### Pipeline Flow

```
Property JSON + Images
        │
        ▼
┌─────────────────────┐
│  ScriptGenerator     │  Validates input, extracts facts,
│  (script_generator)  │  generates scene structure with
│                      │  titles, captions, voiceover scripts
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  AudioEngine         │  Synthesizes narration per scene
│  (audio_engine)      │  (Edge TTS → gTTS → pyttsx3),
│                      │  mixes with BGM via FFmpeg
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  VideoRenderer       │  Generates frames with Ken Burns,
│  (video_renderer)    │  overlays, cross-dissolve transitions,
│                      │  pipes raw RGB → FFmpeg → MP4
└────────┬────────────┘
         │
         ▼
   Output MP4 Video
```

### Key Design Decisions

1. **Template-Based Script Generation (No External AI API)**  
   The voiceover script is generated purely from the input JSON fields using structured templates. This ensures **strict factual adherence** — the video never fabricates or halluccinates details. This was a deliberate choice: a rule-based approach that works reliably and doesn't require API keys or network access.

2. **Cascading TTS Fallbacks**  
   The audio engine tries three TTS providers in order:
   - **Edge TTS** (high-quality neural voices, requires internet)
   - **gTTS** (Google Translate TTS, requires internet)
   - **pyttsx3** (offline system TTS, always available)
   
   This ensures narration works in any environment.

3. **Direct FFmpeg Piping**  
   Instead of writing thousands of individual frame images to disk, frames are rendered in-memory (NumPy arrays) and piped directly to FFmpeg via stdin. This is faster, uses less disk I/O, and avoids temp file cleanup issues.

4. **Precomputed Overlays**  
   Text overlays and gradient scrims are computed once per scene and composited onto every frame, avoiding redundant text rendering per frame.

---

## 🎥 Sample Output

A pre-generated sample video is included at:  
`output/sample_property_tour.mp4`

Generated from `sample_data/property_2bhk_bangalore.json` with the bundled property images and BGM.

**Sample output characteristics:**
- 5 scenes: Intro → Living Room → Kitchen → Bedroom → CTA
- ~25 seconds duration
- 1280×720 (16:9 landscape)
- Neural AI voiceover (Indian English)
- Background music with volume ducking

---

## ⚠️ Limitations

- **No LLM/API dependency**: The script generator uses templates, not an AI language model. This ensures zero-cost, offline operation and factual integrity, but the narration style is less varied than LLM-generated copy.
- **Windows-optimized fonts**: The renderer loads Segoe UI / Arial from Windows Fonts directory. On Linux/Mac it falls back to PIL's default bitmap font.
- **Edge TTS requires internet**: For the highest-quality voices, an internet connection is needed. Offline mode uses pyttsx3 which has lower voice quality.
- **No real-time preview**: The video must be fully rendered before playback. Generation takes ~15–45 seconds depending on scene count.

---

## 🛠️ Technologies & Libraries Used

| Component | Library / Tool | Purpose |
|---|---|---|
| Video Rendering | OpenCV, NumPy, Pillow | Frame generation, image processing, text overlays |
| Video Encoding | FFmpeg (via imageio-ffmpeg) | H.264 MP4 encoding, audio muxing |
| TTS (Primary) | edge-tts | Microsoft Neural TTS voices |
| TTS (Fallback 1) | gTTS | Google Translate TTS |
| TTS (Fallback 2) | pyttsx3 | Offline system TTS |
| Audio Mixing | FFmpeg | Narration + BGM ducking |
| Web UI | Streamlit | Interactive browser-based form |
| Data Format | JSON | Property input schema |

**No external AI APIs or API keys are required.**

---

## 📜 License

This project was created as an assignment submission. All sample data and images are synthetic/royalty-free.

