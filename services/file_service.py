"""
File Service for handling file operations
"""

import shutil
from pathlib import Path
from typing import Optional


class FileService:
    """
    Service class to handle file operations like saving, cleaning, and managing work directories
    """
    
    def __init__(self, work_dir: Path = Path("uploads")):
        self.work_dir = work_dir
        self.work_dir.mkdir(exist_ok=True)
    
    def save_uploaded_file(self, uploaded_file, filename: str) -> Path:
        """Save an uploaded file to the work directory"""
        file_path = self.work_dir / filename
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    
    def clean_work_directory(self) -> bool:
        """Clean all files in the work directory"""
        try:
            shutil.rmtree(self.work_dir)
            self.work_dir.mkdir(exist_ok=True)
            return True
        except Exception:
            return False
    
    def get_output_paths(self, video_path: Path, target_lang: str) -> dict:
        """Get standard output file paths based on video path and target language"""
        return {
            "audio": video_path.with_suffix(".wav"),
            "srt_original": video_path.with_suffix(".srt"),
            "srt_translated": video_path.with_name(f"{video_path.stem}_{target_lang}.srt"),
            "dubbed_audio": video_path.with_name(f"{video_path.stem}_{target_lang}_dubbed.wav"),
            "output_video": video_path.with_name(f"{video_path.stem}_dubbed.mp4"),
            "subtitle_video": video_path.with_name(f"{video_path.stem}_vostfr.mp4"),
            "bg_music": video_path.with_name(f"{video_path.stem}_bg.wav")
        }