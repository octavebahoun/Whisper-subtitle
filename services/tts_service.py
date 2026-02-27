"""
TTS Service for handling text-to-speech operations
"""

from typing import List, Dict, Optional
from pathlib import Path


class TTSService:
    """
    Service class to handle Text-to-Speech operations and voice selection
    """
    
    def __init__(self, available_voices: Dict[str, dict]):
        self.available_voices = available_voices
    
    def get_target_voices(self, target_lang: str) -> List[str]:
        """
        Get list of available voices for a target language
        """
        target_voices = [v for v in self.available_voices.keys() if v.startswith(target_lang)]
        if not target_voices:
            # Handle special cases like zh-CN
            if target_lang == "zh":
                target_voices = [v for v in self.available_voices.keys() if v.startswith("zh-CN")]
            elif target_lang == "en":
                target_voices = [v for v in self.available_voices.keys() if v.startswith("en-US")]
        
        # Fallback to French voices if no specific voices found
        if not target_voices:
            target_voices = ["fr-FR-DeniseNeural", "fr-FR-HenriNeural"]
        
        return target_voices
    
    def get_voices_by_gender(self, gender: str) -> List[str]:
        """
        Get list of voices filtered by gender
        """
        return [
            name for name, info in self.available_voices.items()
            if info["gender"] == gender
        ]
    
    def get_voice_label(self, voice_name: str) -> str:
        """
        Get the display label for a voice
        """
        return self.available_voices.get(voice_name, {}).get('label', voice_name)
    
    def build_speakers_argument(self, selected_speaker: str, all_voices: List[str], enable_diarization: bool) -> str:
        """
        Build the speakers argument for the TTS command
        """
        if enable_diarization:
            voices_to_pass = [selected_speaker]
            other_voices = [v for v in all_voices if v != selected_speaker]
            voices_to_pass.extend(other_voices)
            return ",".join(voices_to_pass)
        else:
            return selected_speaker