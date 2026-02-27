"""
API Service for handling external API communications
"""

import os
import streamlit as st
from typing import Optional


class APIService:
    """
    Service class to handle API key management and external API communications
    """
    
    def __init__(self):
        self._api_key = None
        self._load_api_key()
    
    def _load_api_key(self) -> None:
        """Load API key from environment variables or Streamlit secrets"""
        if "GROQ_API_KEY" in os.environ:
            self._api_key = os.environ.get("GROQ_API_KEY")
        else:
            try:
                if "GROQ_API_KEY" in st.secrets:
                    self._api_key = st.secrets["GROQ_API_KEY"]
            except Exception:
                pass
        
        if not self._api_key:
            st.error(
                "❌ Clé API Groq manquante. "
                "Configurez GROQ_API_KEY dans les secrets (Hugging Face) ou secrets.toml (Local)."
            )
            st.stop()
    
    @property
    def api_key(self) -> str:
        """Get the loaded API key"""
        return self._api_key
    
    def create_env_file(self) -> None:
        """Create a temporary .env file for subprocess communication"""
        with open(".env", "w") as f:
            f.write(f"GROQ_API_KEY={self._api_key}")