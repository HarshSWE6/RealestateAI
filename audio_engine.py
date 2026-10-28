"""
AI Property Video Generator - Audio Engine Module
Handles AI Voiceover narration synthesis (edge-tts / gTTS / pyttsx3),
timing calculation, and background music audio ducking and mixing.
"""

import os
import sys
import asyncio
import logging
import re
import subprocess
from typing import List, Dict, Any, Optional, Tuple
import imageio_ffmpeg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()


class AudioEngine:
    """
    Synthesizes speech narration for each scene and mixes it with background music.
    """

    AVAILABLE_VOICES = {
        "en-IN-NeerjaNeural (Indian English - Female)": "en-IN-NeerjaNeural",
        "en-IN-PrabhatNeural (Indian English - Male)": "en-IN-PrabhatNeural",
        "en-US-ChristopherNeural (US English - Male)": "en-US-ChristopherNeural",
        "en-US-JennyNeural (US English - Female)": "en-US-JennyNeural",
        "en-GB-SoniaNeural (UK English - Female)": "en-GB-SoniaNeural",
    }

    def __init__(self, voice_id: str = "en-IN-NeerjaNeural", temp_dir: str = "output/temp_audio"):
        self.voice_id = voice_id
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)

    def get_audio_duration(self, audio_file: str) -> float:
        """Extracts exact audio duration in seconds using ffmpeg."""
        if not os.path.exists(audio_file):
            return 4.0
        cmd = [FFMPEG_EXE, "-i", audio_file]
        res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
        for line in res.stderr.splitlines():
            if "Duration:" in line:
                match = re.search(r"Duration:\s*(\d+):(\d+):([\d\.]+)", line)
                if match:
                    hours, mins, secs = match.groups()
                    return int(hours) * 3600 + int(mins) * 60 + float(secs)
        return 4.0

    async def _synth_edge_tts(self, text: str, output_path: str, voice: str) -> bool:
        """Synthesizes high-fidelity speech using Microsoft Edge Neural TTS."""
        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            return os.path.exists(output_path) and os.path.getsize(output_path) > 100
        except Exception as e:
            logger.warning(f"edge-tts failed: {e}")
            return False

    def _synth_gtts(self, text: str, output_path: str) -> bool:
        """Fallback to Google Translate TTS."""
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang="en", tld="co.in")
            tts.save(output_path)
            return os.path.exists(output_path) and os.path.getsize(output_path) > 100
        except Exception as e:
            logger.warning(f"gTTS fallback failed: {e}")
            return False

    def _synth_pyttsx3(self, text: str, output_path: str) -> bool:
        """Offline fallback using pyttsx3."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 150)
            engine.save_to_file(text, output_path)
            engine.runAndWait()
            return os.path.exists(output_path) and os.path.getsize(output_path) > 100
        except Exception as e:
            logger.warning(f"pyttsx3 fallback failed: {e}")
            return False

    def generate_narration(self, text: str, scene_idx: int) -> Tuple[Optional[str], float]:
        """
        Generates voiceover audio for a single scene text.
        Returns: (filepath, duration_in_seconds)
        """
        if not text.strip():
            return None, 4.0

        output_file = os.path.join(self.temp_dir, f"scene_{scene_idx:02d}_speech.mp3")

        # 1. Try Edge TTS
        success = False
        try:
            # Handle both standalone and Streamlit (existing event loop) contexts
            try:
                loop = asyncio.get_running_loop()
                # We're inside an existing event loop (e.g., Streamlit/Tornado).
                # Run the coroutine in a brand-new event loop on a separate thread.
                import concurrent.futures
                def _run_tts():
                    return asyncio.run(self._synth_edge_tts(text, output_file, self.voice_id))
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(_run_tts)
                    success = future.result(timeout=30)
            except RuntimeError:
                # No running loop — safe to use asyncio.run() directly
                success = asyncio.run(self._synth_edge_tts(text, output_file, self.voice_id))
        except Exception as e:
            logger.warning(f"Async loop error for edge-tts: {e}")

        # 2. Try gTTS fallback
        if not success:
            logger.info("Falling back to gTTS...")
            success = self._synth_gtts(text, output_file)

        # 3. Try pyttsx3 offline fallback
        if not success:
            logger.info("Falling back to offline pyttsx3...")
            output_file_wav = os.path.join(self.temp_dir, f"scene_{scene_idx:02d}_speech.wav")
            success = self._synth_pyttsx3(text, output_file_wav)
            if success:
                output_file = output_file_wav

        if success and os.path.exists(output_file):
            duration = self.get_audio_duration(output_file)
            # Add a small buffer (0.8s) for scene breathing room
            scene_duration = max(4.0, duration + 0.8)
            return output_file, scene_duration
        else:
            logger.warning(f"Narration generation failed for scene {scene_idx}. Using silent default.")
            return None, 4.5

    def build_full_audio_track(
        self,
        scene_durations: List[float],
        narration_files: List[Optional[str]],
        bgm_path: Optional[str],
        output_audio_path: str,
        bgm_volume: float = 0.15,
        voice_volume: float = 1.0
    ) -> bool:
        """
        Combines scene narrations placed at their respective scene start timestamps,
        and mixes background music with volume ducking.
        """
        total_duration = sum(scene_durations)
        if total_duration <= 0:
            return False

        # Build list of active voice segments with their offset
        inputs = []
        filter_parts = []
        current_time = 0.0

        input_count = 0

        # Collect narration inputs
        narration_stream_labels = []
        for idx, (dur, voice_file) in enumerate(zip(scene_durations, narration_files)):
            if voice_file and os.path.exists(voice_file):
                inputs.extend(["-i", voice_file])
                delay_ms = int(current_time * 1000)
                # adelay filters in milliseconds for L|R channels
                filter_parts.append(
                    f"[{input_count}:a]volume={voice_volume},adelay={delay_ms}|{delay_ms}[v_{input_count}];"
                )
                narration_stream_labels.append(f"[v_{input_count}]")
                input_count += 1
            current_time += dur

        # Handle BGM input
        bgm_input_idx = -1
        if bgm_path and os.path.exists(bgm_path):
            bgm_input_idx = input_count
            inputs.extend(["-stream_loop", "-1", "-i", bgm_path])
            # Trim BGM to total_duration with smooth fade out
            fade_out_start = max(0.0, total_duration - 2.0)
            filter_parts.append(
                f"[{bgm_input_idx}:a]volume={bgm_volume},atrim=0:{total_duration},"
                f"afade=t=in:st=0:d=1,afade=t=out:st={fade_out_start}:d=2[bgm_mix];"
            )
            input_count += 1

        # Combine streams
        if narration_stream_labels and bgm_input_idx >= 0:
            all_labels = "".join(narration_stream_labels) + "[bgm_mix]"
            total_streams = len(narration_stream_labels) + 1
            filter_parts.append(
                f"{all_labels}amix=inputs={total_streams}:duration=longest:dropout_transition=2[outa]"
            )
            final_map = "[outa]"
        elif narration_stream_labels:
            all_labels = "".join(narration_stream_labels)
            total_streams = len(narration_stream_labels)
            if total_streams > 1:
                filter_parts.append(
                    f"{all_labels}amix=inputs={total_streams}:duration=longest[outa]"
                )
                final_map = "[outa]"
            else:
                # Single narration — strip trailing semicolons from filter_parts
                final_map = narration_stream_labels[0]
        elif bgm_input_idx >= 0:
            final_map = "[bgm_mix]"
        else:
            # Generate silent audio track
            cmd = [
                FFMPEG_EXE, "-y",
                "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
                "-t", str(total_duration),
                "-c:a", "aac", output_audio_path
            ]
            subprocess.run(cmd, capture_output=True)
            return os.path.exists(output_audio_path)

        filter_complex = "".join(filter_parts)
        # Remove trailing semicolons that cause FFmpeg filter parse errors
        filter_complex = filter_complex.rstrip(";")

        cmd = [
            FFMPEG_EXE, "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", final_map,
            "-t", str(total_duration),
            "-c:a", "aac",
            "-b:a", "192k",
            output_audio_path
        ]

        logger.info(f"Rendering full audio track: {' '.join(cmd)}")
        res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
        if res.returncode != 0:
            logger.error(f"FFmpeg audio mixing error: {res.stderr}")
            return False

        return os.path.exists(output_audio_path)
