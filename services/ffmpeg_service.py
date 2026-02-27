"""
FFmpeg Service for handling video/audio processing operations
"""

import subprocess
import re
from pathlib import Path
from typing import List, Dict, Optional


class FFmpegService:
    """
    Service class to handle FFmpeg operations for video processing
    """
    
    def __init__(self):
        self.lang_map = {
            "fr": "fre", "en": "eng", "es": "spa", "de": "ger",
            "it": "ita", "pt": "por", "zh": "chi", "ja": "jpn",
            "ko": "kor", "ru": "rus", "ar": "ara", "hi": "hin",
            "nl": "dut", "pl": "pol", "tr": "tur"
        }
    
    def build_ffmpeg_command(
        self,
        video_path: Path,
        output_path: Path,
        srt_path: Optional[Path] = None,
        dubbed_audio_path: Optional[Path] = None,
        bg_music_path: Optional[Path] = None,
        target_lang: str = "fr",
        is_hardcode: bool = False
    ) -> List[str]:
        """
        Build an FFmpeg command based on the provided parameters
        """
        # Map the language code for FFmpeg
        ffmpeg_lang = self.lang_map.get(target_lang, "und")
        
        # Determine if we're doing dubbing or just subtitles
        has_dubbing = dubbed_audio_path and dubbed_audio_path.exists()
        has_bg_music = bg_music_path and bg_music_path.exists()
        
        if has_dubbing:
            # Fusion with dubbed audio
            if has_bg_music:
                # Mix dubbed audio + background music
                cmd = [
                    "ffmpeg", "-y",
                    "-i", str(video_path),
                    "-i", str(dubbed_audio_path),
                    "-i", str(bg_music_path),
                ]
                
                if not is_hardcode and srt_path and srt_path.exists():
                    cmd.extend(["-i", str(srt_path)])
                
                # Volume adjustments and mixing
                cmd.extend([
                    "-filter_complex",
                    "[1:a]volume=1.5[vov];[2:a]volume=0.8[bg];[vov][bg]amix=inputs=2:duration=longest[a]"
                ])
                
                # Video filter if hardcoding subtitles
                if is_hardcode and srt_path:
                    clean_srt_path = str(srt_path).replace(":", "\\:").replace("'", "'\\''")
                    cmd.extend(["-vf", f"subtitles='{clean_srt_path}'"])
                
                # Audio and video mapping
                cmd.extend([
                    "-map", "0:v:0",      # Original video
                    "-map", "[a]",        # Mixed audio
                ])
                
                if not is_hardcode and srt_path and srt_path.exists():
                    cmd.extend(["-map", "3:0"])  # Subtitles
                
                # Video and audio codecs
                cmd.extend([
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "22" if is_hardcode else "copy",
                    "-c:a", "aac", "-b:a", "192k",
                ])
                
                if not is_hardcode and srt_path:
                    cmd.extend([
                        "-c:s", "mov_text",
                        "-metadata:s:s:0", f"language={ffmpeg_lang}",
                        "-metadata:s:s:0", f"title={self._get_language_name(target_lang)}",
                    ])
                
                cmd.extend([
                    "-metadata:s:a:0", f"language={ffmpeg_lang}",
                    str(output_path)
                ])
            else:
                # Dubbing without background music
                cmd = [
                    "ffmpeg", "-y",
                    "-i", str(video_path),
                    "-i", str(dubbed_audio_path),
                ]
                
                if not is_hardcode and srt_path and srt_path.exists():
                    cmd.extend(["-i", str(srt_path)])
                
                # Apply hardcode filter if needed
                if is_hardcode and srt_path:
                    clean_srt_path = str(srt_path).replace(":", "\\:").replace("'", "'\\''")
                    cmd.extend(["-vf", f"subtitles='{clean_srt_path}'"])
                
                # Map streams
                cmd.extend([
                    "-map", "0:v:0",      # Original video
                    "-map", "1:a:0",      # Dubbed audio
                ])
                
                if not is_hardcode and srt_path and srt_path.exists():
                    cmd.extend(["-map", "2:0"])  # Subtitles
                
                # Video and audio codecs
                cmd.extend([
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "22" if is_hardcode else "copy",
                    "-c:a", "aac", "-b:a", "192k",
                ])
                
                if not is_hardcode and srt_path:
                    cmd.extend([
                        "-c:s", "mov_text",
                        "-metadata:s:s:0", f"language={ffmpeg_lang}",
                        "-metadata:s:s:0", f"title={self._get_language_name(target_lang)}",
                    ])
                
                cmd.extend([
                    "-metadata:s:a:0", f"language={ffmpeg_lang}",
                    str(output_path)
                ])
        else:
            # Subtitles only
            if is_hardcode and srt_path:
                # Hardcode subtitles into video
                clean_srt_path = str(srt_path).replace(":", "\\:").replace("'", "'\\''")
                cmd = [
                    "ffmpeg", "-y",
                    "-i", str(video_path),
                    "-vf", f"subtitles='{clean_srt_path}'",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                    "-c:a", "copy",
                    str(output_path)
                ]
            else:
                # Softcode subtitles (as separate stream)
                cmd = [
                    "ffmpeg", "-y",
                    "-i", str(video_path),
                    "-i", str(srt_path) if srt_path else "",
                    "-c", "copy",
                    "-c:s", "mov_text",
                    "-metadata:s:s:0", f"language={ffmpeg_lang}",
                    "-metadata:s:s:0", f"title={self._get_language_name(target_lang)}",
                    str(output_path)
                ]
                # Remove empty string if no srt_path
                if not srt_path:
                    cmd.remove("")
        
        return cmd
    
    def execute_ffmpeg_command(self, cmd: List[str]) -> bool:
        """
        Execute an FFmpeg command and return success status
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _get_language_name(self, lang_code: str) -> str:
        """
        Get the language name from the language code
        This is a simplified version - in a real implementation, 
        this would come from a proper language mapping
        """
        lang_names = {
            "fr": "French", "en": "English", "es": "Spanish", "de": "German",
            "it": "Italian", "pt": "Portuguese", "zh": "Chinese", "ja": "Japanese",
            "ko": "Korean", "ru": "Russian", "ar": "Arabic", "hi": "Hindi",
            "nl": "Dutch", "pl": "Polish", "tr": "Turkish"
        }
        return lang_names.get(lang_code, "Unknown")