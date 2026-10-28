"""
AI Property Video Generator - Video Renderer Module
Direct-to-FFmpeg pipeline with Ken Burns motion, typography overlays,
smooth transitions, and audio synchronization.
"""

import os
import sys
import logging
import math
import tempfile
import subprocess
from typing import List, Dict, Any, Optional, Callable, Tuple
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()


class VideoRenderer:
    """
    Renders high-definition promotional real-estate videos.
    Pipes raw frames directly into FFmpeg for maximum reliability and speed.
    """

    FORMATS = {
        "16:9": (1280, 720),  # Landscape (YouTube, Desktop)
        "9:16": (720, 1280),  # Vertical (Reels, Shorts, Stories)
        "1:1":  (720, 720),   # Square (Social feeds)
    }

    FORMATS_FHD = {
        "16:9": (1920, 1080),
        "9:16": (1080, 1920),
        "1:1":  (1080, 1080),
    }

    def __init__(self, aspect_ratio: str = "16:9", fps: int = 24, high_definition: bool = False):
        self.aspect_ratio = aspect_ratio
        presets = self.FORMATS_FHD if high_definition else self.FORMATS
        self.width, self.height = presets.get(aspect_ratio, (1280, 720))
        self.fps = fps
        self._load_fonts()
        self._precompute_gradient_masks()

    def _load_fonts(self):
        """Loads system fonts with clean cross-platform fallbacks."""
        font_bold_path = None
        font_regular_path = None

        candidate_dirs = [
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"),
            "/usr/share/fonts/truetype/dejavu",
            "/usr/share/fonts/truetype/liberation",
            "/usr/share/fonts/truetype/freefont",
            "/System/Library/Fonts",
            "/Library/Fonts",
        ]

        bold_names = ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "FreeSansBold.ttf", "HelveticaBold.ttf"]
        reg_names = ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf", "FreeSans.ttf", "Helvetica.ttf"]

        for d in candidate_dirs:
            if not os.path.exists(d):
                continue
            if not font_bold_path:
                for b in bold_names:
                    p = os.path.join(d, b)
                    if os.path.exists(p):
                        font_bold_path = p
                        break
            if not font_regular_path:
                for r in reg_names:
                    p = os.path.join(d, r)
                    if os.path.exists(p):
                        font_regular_path = p
                        break
            if font_bold_path and font_regular_path:
                break

        base_scale = self.height / 720.0
        try:
            if font_bold_path and os.path.exists(font_bold_path):
                self.font_title = ImageFont.truetype(font_bold_path, int(34 * base_scale))
                self.font_badge = ImageFont.truetype(font_bold_path, int(18 * base_scale))
                self.font_logo = ImageFont.truetype(font_bold_path, int(22 * base_scale))
            else:
                self.font_title = ImageFont.load_default()
                self.font_badge = ImageFont.load_default()
                self.font_logo = ImageFont.load_default()

            if font_regular_path and os.path.exists(font_regular_path):
                self.font_subtitle = ImageFont.truetype(font_regular_path, int(20 * base_scale))
                self.font_caption = ImageFont.truetype(font_regular_path, int(18 * base_scale))
            else:
                self.font_subtitle = ImageFont.load_default()
                self.font_caption = ImageFont.load_default()
        except Exception as e:
            logger.warning(f"Failed to load TrueType font, using default: {e}")
            self.font_title = ImageFont.load_default()
            self.font_subtitle = ImageFont.load_default()
            self.font_badge = ImageFont.load_default()
            self.font_caption = ImageFont.load_default()
            self.font_logo = ImageFont.load_default()

    def _precompute_gradient_masks(self):
        """Precomputes static gradient scrims for top and bottom bars."""
        # Top gradient: 16% of height
        self.top_h = int(self.height * 0.16)
        top_alphas = np.linspace(170, 0, self.top_h, dtype=np.float32) / 255.0
        self.top_mask = np.tile(top_alphas[:, None, None], (1, self.width, 3))
        self.top_scrim_color = np.array([10, 15, 25], dtype=np.float32)

        # Bottom gradient: 34% of height
        self.bottom_h = int(self.height * 0.34)
        bottom_alphas = (np.linspace(0, 1, self.bottom_h, dtype=np.float32) ** 1.3) * 0.88
        self.bottom_mask = np.tile(bottom_alphas[:, None, None], (1, self.width, 3))
        self.bottom_scrim_color = np.array([8, 12, 20], dtype=np.float32)

    def _get_image(self, image_path: str) -> np.ndarray:
        """Loads image safely, converts to RGB, or creates fallback graphic."""
        if image_path and os.path.exists(image_path):
            try:
                img = cv2.imread(image_path)
                if img is not None:
                    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            except Exception as e:
                logger.warning(f"Error loading image {image_path}: {e}")

        logger.warning(f"Generating fallback graphic for: {image_path}")
        card = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        card[:, :] = [20, 28, 45]
        return card

    def _crop_and_resize(self, img_rgb: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
        """Cover-fits image into target aspect ratio without distortion."""
        h, w, _ = img_rgb.shape
        target_aspect = target_w / target_h
        img_aspect = w / h

        if img_aspect > target_aspect:
            new_w = int(h * target_aspect)
            offset = (w - new_w) // 2
            cropped = img_rgb[:, offset:offset + new_w]
        else:
            new_h = int(w / target_aspect)
            offset = (h - new_h) // 2
            cropped = img_rgb[offset:offset + new_h, :]

        return cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_AREA)

    def _create_scene_overlay(self, scene: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Precomputes the entire text and graphic overlay for a scene ONCE.
        Returns: (overlay_rgb, alpha_mask_float) where shape is (H, W, 3).
        """
        overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # 1. Brand Logo Text (Top Left)
        draw.text((35, 24), "REALTY ASSISTANT", font=self.font_logo, fill=(255, 255, 255, 240))

        # 2. Top Right Badge Pill
        badge_text = scene.get("badge", "")
        if badge_text:
            bbox = draw.textbbox((0, 0), badge_text, font=self.font_badge)
            bw = bbox[2] - bbox[0] + 28
            bh = bbox[3] - bbox[1] + 14
            bx = self.width - bw - 35
            by = 22
            draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=12, fill=(20, 25, 35, 220), outline=(212, 175, 55, 240), width=2)
            draw.text((bx + 14, by + 6), badge_text, font=self.font_badge, fill=(245, 215, 110, 255))

        # 3. Bottom Container
        bottom_start = self.height - self.bottom_h
        margin_x = 40
        text_y = bottom_start + int(self.bottom_h * 0.16)

        # Title
        title = scene.get("title", "")
        draw.text((margin_x, text_y), title, font=self.font_title, fill=(255, 255, 255, 255))
        title_bbox = draw.textbbox((margin_x, text_y), title, font=self.font_title)
        text_y = title_bbox[3] + 6

        # Subtitle
        subtitle = scene.get("subtitle", "")
        if subtitle:
            draw.text((margin_x, text_y), subtitle, font=self.font_subtitle, fill=(200, 215, 235, 240))
            sub_bbox = draw.textbbox((margin_x, text_y), subtitle, font=self.font_subtitle)
            text_y = sub_bbox[3] + 10

        # Caption Bar
        caption = scene.get("caption", "")
        if caption:
            cap_bbox = draw.textbbox((0, 0), caption, font=self.font_caption)
            cw = cap_bbox[2] - cap_bbox[0] + 24
            ch = cap_bbox[3] - cap_bbox[1] + 12
            max_w = self.width - 2 * margin_x
            draw.rounded_rectangle([margin_x, text_y, margin_x + min(cw, max_w), text_y + ch],
                                   radius=8, fill=(12, 18, 28, 200), outline=(90, 130, 190, 120), width=1)
            draw.text((margin_x + 12, text_y + 5), caption, font=self.font_caption, fill=(255, 255, 255, 240))

        # Convert PIL RGBA to numpy
        overlay_arr = np.array(overlay)
        overlay_rgb = overlay_arr[:, :, :3]
        overlay_alpha = (overlay_arr[:, :, 3:4] / 255.0).astype(np.float32)

        return overlay_rgb, overlay_alpha

    def _apply_ken_burns(self, base_img: np.ndarray, progress: float, zoom_in: bool = True) -> np.ndarray:
        """Applies smooth Ken Burns zoom and slight pan."""
        max_zoom = 1.06
        if zoom_in:
            scale = 1.0 + (max_zoom - 1.0) * progress
        else:
            scale = max_zoom - (max_zoom - 1.0) * progress

        target_w = int(self.width * scale)
        target_h = int(self.height * scale)

        resized = cv2.resize(base_img, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

        pan_offset_x = int((target_w - self.width) * (0.5 + 0.08 * math.sin(progress * math.pi)))
        pan_offset_y = int((target_h - self.height) * 0.5)

        pan_offset_x = max(0, min(pan_offset_x, target_w - self.width))
        pan_offset_y = max(0, min(pan_offset_y, target_h - self.height))

        return resized[pan_offset_y:pan_offset_y + self.height, pan_offset_x:pan_offset_x + self.width]

    def _composite_frame(
        self,
        ken_burns_frame: np.ndarray,
        overlay_rgb: np.ndarray,
        overlay_alpha: np.ndarray,
        progress: float
    ) -> np.ndarray:
        """Composites gradient scrims, text overlays, and progress bar."""
        frame = ken_burns_frame.copy().astype(np.float32)

        # 1. Apply Top Scrim
        frame[:self.top_h] = (
            frame[:self.top_h] * (1.0 - self.top_mask) + self.top_scrim_color * self.top_mask
        )

        # 2. Apply Bottom Scrim
        b_start = self.height - self.bottom_h
        frame[b_start:] = (
            frame[b_start:] * (1.0 - self.bottom_mask) + self.bottom_scrim_color * self.bottom_mask
        )

        # 3. Apply Text & Badges Overlay
        mask = (overlay_alpha > 0.01)
        if np.any(mask):
            frame = frame * (1.0 - overlay_alpha) + overlay_rgb * overlay_alpha

        res = np.clip(frame, 0, 255).astype(np.uint8)

        # 4. Progress bar at bottom
        bar_w = int(self.width * progress)
        if bar_w > 0:
            res[-5:, :bar_w] = [212, 175, 55]

        return res

    def render_video(
        self,
        scenes: List[Dict[str, Any]],
        scene_durations: List[float],
        audio_track_path: Optional[str],
        output_mp4_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> bool:
        """
        Renders full video combining Ken Burns motion, typography, transitions, and audio
        by piping raw RGB frames directly to FFmpeg.
        """
        if not scenes:
            logger.error("No scenes provided for video rendering.")
            return False

        os.makedirs(os.path.dirname(output_mp4_path) or ".", exist_ok=True)

        # Pre-process & fit images
        logger.info(f"Fitting {len(scenes)} property images to ({self.width}x{self.height})...")
        base_images = []
        for s in scenes:
            raw_img = self._get_image(s.get("image_path", ""))
            fitted_img = self._crop_and_resize(raw_img, self.width, self.height)
            base_images.append(fitted_img)

        # Pre-compute static overlays
        logger.info("Pre-computing graphic and text overlays...")
        scene_overlays = [self._create_scene_overlay(s) for s in scenes]

        total_scenes = len(scenes)
        transition_duration = 0.5
        transition_frames = int(transition_duration * self.fps)

        total_frames = sum(int(dur * self.fps) for dur in scene_durations)
        frames_rendered = 0

        # Construct FFmpeg command with piped rawvideo input and audio track input
        cmd = [
            FFMPEG_EXE, "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{self.width}x{self.height}",
            "-pix_fmt", "rgb24",
            "-r", str(self.fps),
            "-i", "-"
        ]

        if audio_track_path and os.path.exists(audio_track_path):
            cmd.extend([
                "-i", audio_track_path,
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest"
            ])
        else:
            cmd.extend(["-an"])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_mp4_path
        ])

        logger.info(f"Launching FFmpeg pipe: {' '.join(cmd)}")
        with tempfile.TemporaryFile() as stderr_file:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=stderr_file)

            try:
                for idx, (scene, duration, base_img) in enumerate(zip(scenes, scene_durations, base_images)):
                    scene_frames = int(duration * self.fps)
                    zoom_in = (idx % 2 == 0)
                    overlay_rgb, overlay_alpha = scene_overlays[idx]

                    for f in range(scene_frames):
                        progress = f / max(1, scene_frames - 1)
                        kb_frame = self._apply_ken_burns(base_img, progress, zoom_in=zoom_in)
                        current_frame_rgb = self._composite_frame(kb_frame, overlay_rgb, overlay_alpha, progress)

                        # Cross-dissolve into next scene
                        if idx < total_scenes - 1 and (scene_frames - f) <= transition_frames:
                            next_base_img = base_images[idx + 1]
                            next_zoom_in = ((idx + 1) % 2 == 0)
                            next_overlay_rgb, next_overlay_alpha = scene_overlays[idx + 1]
                            t_progress = (transition_frames - (scene_frames - f)) / transition_frames
                            
                            next_kb_frame = self._apply_ken_burns(next_base_img, 0.0, zoom_in=next_zoom_in)
                            next_frame_rgb = self._composite_frame(next_kb_frame, next_overlay_rgb, next_overlay_alpha, 0.0)

                            blended_rgb = cv2.addWeighted(
                                current_frame_rgb, 1.0 - t_progress,
                                next_frame_rgb, t_progress,
                                0
                            )
                            frame_bytes = blended_rgb.tobytes()
                        else:
                            frame_bytes = current_frame_rgb.tobytes()

                        proc.stdin.write(frame_bytes)
                        frames_rendered += 1

                        if progress_callback and frames_rendered % 24 == 0:
                            pct = min(0.95, frames_rendered / max(1, total_frames))
                            progress_callback(pct, f"Rendering Scene {idx + 1}/{total_scenes} ({int(pct*100)}%)")

                proc.stdin.close()
                proc.wait()
                if proc.returncode != 0:
                    stderr_file.seek(0)
                    stderr_output = stderr_file.read().decode("utf-8", errors="ignore")
                    logger.error(f"FFmpeg failed with returncode {proc.returncode}: {stderr_output[-500:]}")
                    return False

            except Exception as e:
                logger.error(f"Exception during frame piping: {e}")
                proc.kill()
                return False

        if progress_callback:
            progress_callback(1.0, "Video generated successfully!")

        return os.path.exists(output_mp4_path) and os.path.getsize(output_mp4_path) > 1000
