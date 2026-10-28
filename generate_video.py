"""
AI Property Video Generator - Main CLI Orchestrator
Command-line tool to generate high quality real estate videos from property details and photos.
"""

import os
import sys
import argparse
import json
import logging
from typing import Dict, Any

from script_generator import ScriptGenerator, load_property_json
from audio_engine import AudioEngine
from video_renderer import VideoRenderer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("PropertyVideoGenerator")


def build_property_video(
    property_data: Dict[str, Any],
    output_path: str = "output/sample_property_tour.mp4",
    aspect_ratio: str = "16:9",
    voice_id: str = "en-IN-NeerjaNeural",
    enable_narration: bool = True,
    enable_bgm: bool = True,
    bgm_path: str = None,
    progress_callback=None
) -> str:
    """
    Unified pipeline that builds the complete real estate video.
    """
    logger.info("==================================================")
    logger.info("   AI PROPERTY VIDEO GENERATOR - REALTY ASSISTANT ")
    logger.info("==================================================")

    # 1. Validation & Script Generation
    script_gen = ScriptGenerator()
    validation_errors = script_gen.validate_property_data(property_data)
    if validation_errors:
        for err in validation_errors:
            logger.warning(f"Validation Notice: {err}")

    scenes = script_gen.generate_scenes(property_data)
    logger.info(f"Generated {len(scenes)} scenes strictly from supplied property facts.")

    for s in scenes:
        logger.info(f"  [Scene {s['scene_index'] + 1}] Type: {s['scene_type'].upper()} | Title: '{s['title']}'")
        logger.info(f"     Script: \"{s['voiceover']}\"")

    # 2. Audio & Narration Processing
    audio_engine = AudioEngine(voice_id=voice_id)
    scene_durations = []
    narration_files = []

    if enable_narration:
        logger.info(f"Synthesizing Neural AI Voiceover using '{voice_id}'...")
        for idx, s in enumerate(scenes):
            if progress_callback:
                progress_callback(0.05 + 0.15 * (idx / len(scenes)), f"Synthesizing voiceover for scene {idx + 1}...")
            voice_file, dur = audio_engine.generate_narration(s["voiceover"], idx)
            narration_files.append(voice_file)
            scene_durations.append(dur)
            logger.info(f"  Scene {idx + 1} voiceover ready (Duration: {dur:.2f}s)")
    else:
        logger.info("Voiceover disabled. Using standard 4.5s per scene pacing.")
        scene_durations = [4.5] * len(scenes)
        narration_files = [None] * len(scenes)

    # 3. Audio Mixing (Narration + BGM)
    mixed_audio_path = os.path.join(audio_engine.temp_dir, "master_audio_track.aac")
    active_bgm = None
    if enable_bgm:
        active_bgm = bgm_path or property_data.get("bgm_audio")
        if active_bgm and not os.path.exists(active_bgm):
            logger.warning(f"Specified BGM not found: {active_bgm}. Checking default sample...")
            fallback_bgm = "sample_data/bgm_luxury.wav"
            active_bgm = fallback_bgm if os.path.exists(fallback_bgm) else None

    logger.info(f"Mixing master audio track (Narration + BGM: {bool(active_bgm)})...")
    audio_success = audio_engine.build_full_audio_track(
        scene_durations=scene_durations,
        narration_files=narration_files,
        bgm_path=active_bgm,
        output_audio_path=mixed_audio_path,
        bgm_volume=0.14,
        voice_volume=1.0
    )

    final_audio = mixed_audio_path if audio_success else None

    # 4. Video Rendering
    total_duration = sum(scene_durations)
    logger.info(f"Rendering Video ({aspect_ratio}, Total Duration: {total_duration:.1f}s, Scenes: {len(scenes)})...")
    renderer = VideoRenderer(aspect_ratio=aspect_ratio, fps=24)
    render_success = renderer.render_video(
        scenes=scenes,
        scene_durations=scene_durations,
        audio_track_path=final_audio,
        output_mp4_path=output_path,
        progress_callback=progress_callback
    )

    if not render_success or not os.path.exists(output_path):
        raise RuntimeError("Video rendering pipeline encountered an error.")

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    logger.info("==================================================")
    logger.info("SUCCESSFULLY GENERATED PROPERTY VIDEO!")
    logger.info(f"File Path    : {os.path.abspath(output_path)}")
    logger.info(f"Duration     : {total_duration:.1f} seconds")
    logger.info(f"File Size    : {size_mb:.2f} MB")
    logger.info(f"Aspect Ratio : {aspect_ratio}")
    logger.info("==================================================")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="AI Property Video Generator - Turn real-estate photos and metadata into short promo videos."
    )
    parser.add_argument(
        "--input", "-i",
        default="sample_data/property_2bhk_bangalore.json",
        help="Path to property JSON file (default: sample_data/property_2bhk_bangalore.json)"
    )
    parser.add_argument(
        "--output", "-o",
        default="output/sample_property_tour.mp4",
        help="Output MP4 file path (default: output/sample_property_tour.mp4)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["16:9", "9:16", "1:1"],
        default="16:9",
        help="Aspect ratio format: 16:9 (Landscape), 9:16 (Reel/Mobile), 1:1 (Square)"
    )
    parser.add_argument(
        "--voice", "-v",
        default="en-IN-NeerjaNeural",
        help="Edge TTS voice model (e.g. en-IN-NeerjaNeural, en-US-ChristopherNeural)"
    )
    parser.add_argument(
        "--bgm",
        default=None,
        help="Path to custom background audio file (.wav or .mp3)"
    )
    parser.add_argument(
        "--no-narration",
        action="store_true",
        help="Disable AI voiceover narration"
    )
    parser.add_argument(
        "--no-bgm",
        action="store_true",
        help="Disable background music"
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)

    try:
        data = load_property_json(args.input)
    except Exception as e:
        logger.error(f"Failed to read JSON: {e}")
        sys.exit(1)

    try:
        build_property_video(
            property_data=data,
            output_path=args.output,
            aspect_ratio=args.format,
            voice_id=args.voice,
            enable_narration=not args.no_narration,
            enable_bgm=not args.no_bgm,
            bgm_path=args.bgm
        )
    except Exception as e:
        logger.exception(f"Execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
