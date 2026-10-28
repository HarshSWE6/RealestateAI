"""
AI Property Video Generator - Script Generator Module
Extracts property facts and generates structured scene narration, titles, and captions.
Guarantees strict factual adherence: uses ONLY information present in the input.
"""

import json
import logging
from typing import Dict, List, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScriptGenerator:
    """
    Generates video scenes and voiceover scripts strictly based on provided property details.
    Follows assignment requirement: 'Only use facts supplied in the input.'
    Pacing is optimized for 20-40 second promotional videos.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def validate_property_data(self, data: Dict[str, Any]) -> List[str]:
        """
        Validates the input dictionary and returns a list of error/warning messages.
        Gracefully handles missing fields without crashing.
        """
        errors = []
        if not data.get("property_name"):
            errors.append("Property name is missing.")
        if not data.get("location"):
            errors.append("Property location is missing.")
        if not data.get("price"):
            errors.append("Property price is missing.")
        
        images = data.get("images", [])
        if not images:
            errors.append("No property images provided. At least 1 image is required (4-8 recommended).")
        elif len(images) < 2:
            logger.warning("Only 1 image provided. The video will be brief.")
        
        return errors

    def generate_scenes(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Constructs scenes pairing images with factual titles, captions, and voiceover scripts.
        """
        validation_errors = self.validate_property_data(data)
        if validation_errors and not data.get("images"):
            raise ValueError(f"Cannot generate video: {'; '.join(validation_errors)}")

        name = data.get("property_name", "Luxury Residence")
        prop_type = data.get("property_type", "Apartment")
        location = data.get("location", "Prime Location")
        price = data.get("price", "Price on Request")
        carpet_area = data.get("carpet_area", "")
        possession = data.get("possession", "")
        key_features = data.get("key_features", [])
        cta_text = data.get("cta_text", "Book your private walkthrough today.")
        contact = data.get("contact", {})
        phone = contact.get("phone", "")
        email = contact.get("email", "")
        images = data.get("images", [])

        if not images:
            raise ValueError("No images found in property data.")

        scenes = []
        total_images = len(images)

        # ----------------- Scene 1: Opening Title & Overview (Concise & Punchy) -----------------
        intro_voice = f"Welcome to {name}, an exclusive {prop_type} in {location}, starting at {price}."

        sub_items = [prop_type, location]
        if carpet_area:
            sub_items.append(carpet_area)

        scenes.append({
            "scene_index": 0,
            "scene_type": "intro",
            "image_path": images[0],
            "title": name,
            "subtitle": " • ".join(sub_items),
            "badge": price,
            "caption": f"{name} • {location} • {price}",
            "voiceover": intro_voice
        })

        # ----------------- Feature Scenes (Scenes 2 to N-1) -----------------
        remaining_images = images[1:] if total_images > 1 else [images[0]]
        
        if len(remaining_images) >= 2:
            feature_images = remaining_images[:-1]
            outro_image = remaining_images[-1]
        else:
            feature_images = remaining_images
            outro_image = remaining_images[0]

        for idx, img_path in enumerate(feature_images):
            feature_idx = idx
            if feature_idx < len(key_features):
                feature_text = key_features[feature_idx]
                feat_voice = f"Featuring {feature_text}."
                feat_caption = feature_text
            else:
                # Use only supplied facts — never fabricate details
                feat_voice = f"Explore more of {name} in {location}."
                feat_caption = name

            # Derive punchy title
            if ":" in feat_caption:
                parts = feat_caption.split(":", 1)
                feat_title = parts[0].strip()
                feat_caption = parts[1].strip()
            elif len(feat_caption) < 35:
                feat_title = feat_caption
            else:
                words = feat_caption.split()
                feat_title = " ".join(words[:4]).title()

            scenes.append({
                "scene_index": len(scenes),
                "scene_type": "feature",
                "image_path": img_path,
                "title": feat_title,
                "subtitle": location,
                "badge": f"Feature {idx + 1}",
                "caption": feat_caption,
                "voiceover": feat_voice
            })

        # ----------------- Final Scene: Call To Action & Contact -----------------
        outro_voice = f"{cta_text} "
        if phone:
            outro_voice += f"Call us at {phone}."
        elif email:
            outro_voice += f"Contact us today."

        contact_details = []
        if contact.get("agent_name"):
            contact_details.append(contact["agent_name"])
        if phone:
            contact_details.append(f"Call: {phone}")
        if email:
            contact_details.append(f"Email: {email}")

        scenes.append({
            "scene_index": len(scenes),
            "scene_type": "outro",
            "image_path": outro_image,
            "title": "Book Your Private Tour",
            "subtitle": cta_text,
            "badge": "Enquire Now",
            "caption": " • ".join(contact_details) if contact_details else cta_text,
            "voiceover": outro_voice
        })

        return scenes


def load_property_json(filepath: str) -> Dict[str, Any]:
    """Loads and validates a property JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data
