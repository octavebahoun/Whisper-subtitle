"""
Configuration module for Whisper Subtitle Generator
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class AppConfig:
    """Application configuration settings"""
    work_dir: Path = Path("uploads")
    tts_languages: List[str] = None
    tts_speakers: Dict[str, dict] = None
    whisper_languages: Dict[str, dict] = None
    target_languages: Dict[str, dict] = None
    
    def __post_init__(self):
        if self.tts_languages is None:
            self.tts_languages = ["fr", "en", "ja", "zh", "ko", "de", "es", "it", "pt", "ru"]
        
        if self.tts_speakers is None:
            self.tts_speakers = {
                # Français
                "fr-FR-DeniseNeural": {"gender": "female", "native": "Français", "label": "Denise (FR)"},
                "fr-FR-HenriNeural": {"gender": "male", "native": "Français", "label": "Henri (FR)"},
                "fr-FR-EloiseNeural": {"gender": "female", "native": "Français", "label": "Eloise (FR)"},
                # Anglais
                "en-US-AriaNeural": {"gender": "female", "native": "Anglais", "label": "Aria (US)"},
                "en-US-GuyNeural": {"gender": "male", "native": "Anglais", "label": "Guy (US)"},
                "en-US-JennyNeural": {"gender": "female", "native": "Anglais", "label": "Jenny (US)"},
                # Japonais
                "ja-JP-NanamiNeural": {"gender": "female", "native": "Japonais", "label": "Nanami (JP)"},
                "ja-JP-KeitaNeural": {"gender": "male", "native": "Japonais", "label": "Keita (JP)"},
            }

# Global configuration instance
config = AppConfig()