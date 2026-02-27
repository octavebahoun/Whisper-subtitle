"""
Progress tracking utilities for the application
"""

import streamlit as st
from typing import Optional


class ProgressTracker:
    """
    Utility class to track and display progress during processing
    """
    
    def __init__(self, total_steps: int):
        self.total_steps = total_steps
        self.current_step = 0
        self.progress_bar = st.progress(0)
        self.status_text = st.empty()
    
    def update(self, step: int, message: str) -> None:
        """
        Update the progress bar and status message
        """
        self.current_step = step
        progress_percentage = min(100, int((step / self.total_steps) * 100))
        self.progress_bar.progress(progress_percentage)
        self.status_text.info(message)
    
    def complete(self) -> None:
        """
        Mark the process as complete
        """
        self.progress_bar.progress(100)
        self.status_text.success("✅ Traitement terminé avec succès !")
    
    def reset(self) -> None:
        """
        Reset the progress tracker
        """
        self.current_step = 0
        self.progress_bar.progress(0)
        self.status_text.empty()