"""
Module de cache pour les traductions.
Évite de re-traduire des textes déjà traduits.
"""

import json
import hashlib
from pathlib import Path
from typing import Optional

# Fichier de cache
CACHE_FILE = Path(__file__).parent / "translations_cache.json"


def get_cache_key(text: str, source_lang: str, target_lang: str) -> str:
    """Génère une clé unique pour le cache basée sur le texte et les langues."""
    content = f"{source_lang}:{target_lang}:{text}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def load_cache() -> dict:
    """Charge le cache depuis le fichier JSON."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_cache(cache: dict) -> None:
    """Sauvegarde le cache dans le fichier JSON."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"⚠️ Impossible de sauvegarder le cache: {e}")


def get_cached_translation(text: str, source_lang: str, target_lang: str) -> Optional[str]:
    """
    Récupère une traduction depuis le cache.
    
    Args:
        text: Texte source à traduire
        source_lang: Code de la langue source (ex: "ja", "en")
        target_lang: Code de la langue cible (ex: "fr")
    
    Returns:
        La traduction mise en cache ou None si non trouvée
    """
    cache = load_cache()
    key = get_cache_key(text, source_lang, target_lang)
    return cache.get(key)


def cache_translation(text: str, translation: str, source_lang: str, target_lang: str) -> None:
    """
    Met en cache une traduction.
    
    Args:
        text: Texte source
        translation: Texte traduit
        source_lang: Code de la langue source
        target_lang: Code de la langue cible
    """
    cache = load_cache()
    key = get_cache_key(text, source_lang, target_lang)
    cache[key] = {
        "source": text,
        "translation": translation,
        "source_lang": source_lang,
        "target_lang": target_lang
    }
    save_cache(cache)


def get_cache_stats() -> dict:
    """Retourne des statistiques sur le cache."""
    cache = load_cache()
    return {
        "total_entries": len(cache),
        "languages": list(set(
            f"{v['source_lang']}→{v['target_lang']}" 
            for v in cache.values() 
            if isinstance(v, dict)
        ))
    }


def clear_cache() -> None:
    """Vide complètement le cache."""
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()
        print("🗑️ Cache de traductions vidé")
