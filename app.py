"""
AI Property Video Generator - Streamlit Web Application
Interactive web form for creating real-estate promotional videos
from property details and photos.
"""

import os
import sys
import json
import tempfile
import shutil
import logging
import streamlit as st
from typing import Dict, Any, List

# Ensure the project root is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from script_generator import ScriptGenerator
from audio_engine import AudioEngine
from video_renderer import VideoRenderer
from generate_video import build_property_video

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Page Configuration ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Property Video Generator",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .main-header h1 {
        color: #d4af37;
        font-size: 2.2rem;
        margin-bottom: 0.3rem;
    }
    .main-header p {
        color: #c0c8d8;
        font-size: 1rem;
    }
    .stButton > button {
        background-color: #d4af37;
        color: #1a1a2e;
        font-weight: bold;
        border: none;
        padding: 0.6rem 2rem;
        border-radius: 8px;
        font-size: 1rem;
    }
    .stButton > button:hover {
        background-color: #b8962e;
        color: #fff;
    }
    .success-box {
        background-color: #0d3b0d;
        border: 1px solid #2ecc40;
        border-radius: 8px;
        padding: 1rem;
        color: #2ecc40;
    }
    .info-card {
        background: #1e293b;
        border-radius: 10px;
        padding: 1.2rem;
        border: 1px solid #334155;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def save_uploaded_images(uploaded_files) -> List[str]:
    """Save uploaded image files to a temp directory and return their paths."""
    temp_dir = os.path.join("output", "uploaded_images")
    os.makedirs(temp_dir, exist_ok=True)
    saved_paths = []
    for idx, file in enumerate(uploaded_files):
        ext = os.path.splitext(file.name)[1] or ".jpg"
        save_path = os.path.join(temp_dir, f"image_{idx+1:02d}{ext}")
        with open(save_path, "wb") as f:
            f.write(file.getbuffer())
        saved_paths.append(save_path)
    return saved_paths


def save_uploaded_bgm(uploaded_bgm) -> str:
    """Save uploaded BGM file and return its path."""
    temp_dir = os.path.join("output", "uploaded_bgm")
    os.makedirs(temp_dir, exist_ok=True)
    ext = os.path.splitext(uploaded_bgm.name)[1] or ".wav"
    save_path = os.path.join(temp_dir, f"bgm_custom{ext}")
    with open(save_path, "wb") as f:
        f.write(uploaded_bgm.getbuffer())
    return save_path


def load_sample_data() -> Dict[str, Any]:
    """Load the bundled sample property data."""
    sample_path = os.path.join("sample_data", "property_2bhk_bangalore.json")
    if os.path.exists(sample_path):
        with open(sample_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def main():
    # ─── Header ───────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="main-header">
        <h1>🏠 AI Property Video Generator</h1>
        <p>Transform property photos and details into professional promotional videos in minutes</p>
    </div>
    """, unsafe_allow_html=True)

    # ─── Sidebar: Settings ────────────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Video Settings")

        aspect_ratio = st.selectbox(
            "📐 Aspect Ratio",
            options=["16:9", "9:16", "1:1"],
            index=0,
            help="16:9 for YouTube/Desktop, 9:16 for Reels/Shorts, 1:1 for Social Feeds"
        )

        voice_options = {
            "🇮🇳 Neerja (Indian English - Female)": "en-IN-NeerjaNeural",
            "🇮🇳 Prabhat (Indian English - Male)": "en-IN-PrabhatNeural",
            "🇺🇸 Christopher (US English - Male)": "en-US-ChristopherNeural",
            "🇺🇸 Jenny (US English - Female)": "en-US-JennyNeural",
            "🇬🇧 Sonia (UK English - Female)": "en-GB-SoniaNeural",
        }
        selected_voice_label = st.selectbox(
            "🎤 AI Voice",
            options=list(voice_options.keys()),
            index=0,
            help="Select the Neural AI voice for narration"
        )
        voice_id = voice_options[selected_voice_label]

        enable_narration = st.checkbox("🔊 Enable AI Voiceover", value=True)
        enable_bgm = st.checkbox("🎵 Enable Background Music", value=True)

        st.divider()
        st.caption("Built with ❤️ for Realty Assistant")

    # ─── Main Content: Two Tabs ───────────────────────────────────────────────
    tab_form, tab_json, tab_sample = st.tabs([
        "📝 Property Form", "📄 Upload JSON", "🏗️ Sample Demo"
    ])

    property_data = None
    custom_bgm_path = None

    # ─── TAB 1: Interactive Property Form ─────────────────────────────────────
    with tab_form:
        st.subheader("Enter Property Details")

        col1, col2 = st.columns(2)
        with col1:
            prop_name = st.text_input("🏷️ Property Name", placeholder="e.g., The Azure Residences")
            prop_type = st.text_input("🏢 Property Type", placeholder="e.g., 2-BHK Luxury Apartment")
            location = st.text_input("📍 Location", placeholder="e.g., Whitefield, Bengaluru")
        with col2:
            price = st.text_input("💰 Price", placeholder="e.g., ₹1.25 Crore")
            carpet_area = st.text_input("📏 Carpet Area", placeholder="e.g., 1,450 sq.ft.")
            possession = st.text_input("📅 Possession Status", placeholder="e.g., Ready to Move")

        st.markdown("---")
        st.subheader("✨ Key Features")
        st.caption("Add one feature per line. These become scene descriptions in the video.")
        features_text = st.text_area(
            "Features (one per line)",
            height=150,
            placeholder="Grand architecture with landscaped entrance\nSpacious living room with Italian marble\nModern modular kitchen\nMaster bedroom with city views\nRooftop infinity pool",
            label_visibility="collapsed"
        )

        st.markdown("---")
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            agent_name = st.text_input("👤 Agent / Company Name", placeholder="Realty Assistant")
        with col_c2:
            phone = st.text_input("📞 Phone Number", placeholder="+91 98765 43210")
        with col_c3:
            email = st.text_input("📧 Email", placeholder="sales@example.com")
        cta_text = st.text_input("📢 Call-to-Action Text", value="Book your exclusive private walkthrough today!")

        st.markdown("---")
        st.subheader("📸 Upload Property Images")
        st.caption("Upload 4-8 high-quality property photos (JPG/PNG). Order matters: first image is the intro scene.")
        uploaded_images = st.file_uploader(
            "Select Images",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            label_visibility="collapsed"
        )

        if uploaded_images:
            cols = st.columns(min(len(uploaded_images), 5))
            for idx, img_file in enumerate(uploaded_images):
                with cols[idx % 5]:
                    st.image(img_file, caption=f"Image {idx+1}", use_container_width=True)

        st.subheader("🎵 Background Music (Optional)")
        uploaded_bgm = st.file_uploader(
            "Upload custom BGM (.wav or .mp3)",
            type=["wav", "mp3"],
            label_visibility="collapsed"
        )

        if st.button("🎬 Generate Video", key="form_generate", use_container_width=True):
            # Validate minimum input
            if not prop_name:
                st.error("❌ Property Name is required.")
            elif not uploaded_images:
                st.error("❌ Please upload at least one property image.")
            else:
                # Save uploaded images
                image_paths = save_uploaded_images(uploaded_images)
                if uploaded_bgm:
                    custom_bgm_path = save_uploaded_bgm(uploaded_bgm)

                key_features = [f.strip() for f in features_text.strip().split("\n") if f.strip()] if features_text.strip() else []

                property_data = {
                    "property_name": prop_name,
                    "property_type": prop_type or "Apartment",
                    "location": location or "Prime Location",
                    "price": price or "Price on Request",
                    "carpet_area": carpet_area,
                    "possession": possession,
                    "key_features": key_features,
                    "contact": {
                        "agent_name": agent_name,
                        "phone": phone,
                        "email": email,
                    },
                    "cta_text": cta_text or "Book your private walkthrough today.",
                    "images": image_paths,
                }
                if custom_bgm_path:
                    property_data["bgm_audio"] = custom_bgm_path

                st.session_state["property_data"] = property_data
                st.session_state["generate_requested"] = True
                st.session_state["custom_bgm"] = custom_bgm_path

    # ─── TAB 2: Upload JSON ──────────────────────────────────────────────────
    with tab_json:
        st.subheader("Upload Property JSON File")
        st.caption("Upload a JSON file matching the expected schema. See sample_data/property_2bhk_bangalore.json for reference.")

        uploaded_json = st.file_uploader("Select JSON file", type=["json"], label_visibility="collapsed")

        if uploaded_json:
            try:
                json_data = json.load(uploaded_json)
                st.json(json_data)
                st.success("✅ JSON loaded successfully!")

                json_images = st.file_uploader(
                    "📸 Upload matching images (in the same order as listed in JSON)",
                    type=["jpg", "jpeg", "png", "webp"],
                    accept_multiple_files=True,
                    key="json_images",
                )

                if st.button("🎬 Generate Video from JSON", key="json_generate", use_container_width=True):
                    if json_images:
                        image_paths = save_uploaded_images(json_images)
                        json_data["images"] = image_paths
                    elif not json_data.get("images"):
                        st.error("❌ No images found in JSON or uploaded. Please provide images.")
                        st.stop()

                    st.session_state["property_data"] = json_data
                    st.session_state["generate_requested"] = True
                    st.session_state["custom_bgm"] = None

            except json.JSONDecodeError as e:
                st.error(f"❌ Invalid JSON file: {e}")

    # ─── TAB 3: Sample Demo ──────────────────────────────────────────────────
    with tab_sample:
        st.subheader("🏗️ Quick Demo with Sample Data")
        st.info("Click below to generate a video using the bundled sample property data (The Azure Residences, Whitefield).")

        sample_data = load_sample_data()
        if sample_data:
            with st.expander("📋 Preview Sample Data", expanded=False):
                st.json(sample_data)

            if st.button("🎬 Generate Sample Video", key="sample_generate", use_container_width=True):
                st.session_state["property_data"] = sample_data
                st.session_state["generate_requested"] = True
                st.session_state["custom_bgm"] = None
        else:
            st.warning("Sample data file not found at sample_data/property_2bhk_bangalore.json")

    # ─── Video Generation Pipeline ────────────────────────────────────────────
    if st.session_state.get("generate_requested"):
        st.session_state["generate_requested"] = False
        data = st.session_state.get("property_data", {})
        bgm = st.session_state.get("custom_bgm")

        if not data:
            st.error("No property data available.")
            return

        st.markdown("---")
        st.subheader("🎬 Video Generation Progress")

        progress_bar = st.progress(0, text="Initializing pipeline...")
        status_text = st.empty()

        def update_progress(pct: float, msg: str):
            progress_bar.progress(min(pct, 1.0), text=msg)
            status_text.caption(msg)

        output_path = os.path.join("output", "generated_property_video.mp4")

        try:
            update_progress(0.02, "Validating property data...")

            result_path = build_property_video(
                property_data=data,
                output_path=output_path,
                aspect_ratio=aspect_ratio,
                voice_id=voice_id,
                enable_narration=enable_narration,
                enable_bgm=enable_bgm,
                bgm_path=bgm,
                progress_callback=update_progress,
            )

            progress_bar.progress(1.0, text="✅ Video generated successfully!")

            st.success("🎉 Your property video is ready!")

            # Show video preview
            if os.path.exists(result_path):
                file_size_mb = os.path.getsize(result_path) / (1024 * 1024)

                col_v1, col_v2 = st.columns([3, 1])
                with col_v1:
                    st.video(result_path)
                with col_v2:
                    st.metric("File Size", f"{file_size_mb:.1f} MB")
                    st.metric("Format", aspect_ratio)
                    st.metric("Voice", selected_voice_label.split("(")[0].strip())

                    # Download button
                    with open(result_path, "rb") as vid_file:
                        st.download_button(
                            label="⬇️ Download Video",
                            data=vid_file.read(),
                            file_name=f"{data.get('property_name', 'property').replace(' ', '_')}_tour.mp4",
                            mime="video/mp4",
                            use_container_width=True,
                        )

        except Exception as e:
            progress_bar.progress(0, text="❌ Generation failed")
            st.error(f"Video generation failed: {e}")
            logger.exception(f"Pipeline error: {e}")


if __name__ == "__main__":
    main()

