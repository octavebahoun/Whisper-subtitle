"""
Module de gestion des langues supportées.
Définit les langues source et cible disponibles pour la transcription et la traduction.
"""

# Langues supportées par Whisper pour la transcription
WHISPER_LANGUAGES = {
    "ja": {"name": "Japonais", "emoji": "🇯🇵", "whisper_code": "ja"},
    "en": {"name": "Anglais", "emoji": "🇬🇧", "whisper_code": "en"},
    "zh": {"name": "Chinois", "emoji": "🇨🇳", "whisper_code": "zh"},
    "ko": {"name": "Coréen", "emoji": "🇰🇷", "whisper_code": "ko"},
    "es": {"name": "Espagnol", "emoji": "🇪🇸", "whisper_code": "es"},
    "de": {"name": "Allemand", "emoji": "🇩🇪", "whisper_code": "de"},
    "it": {"name": "Italien", "emoji": "🇮🇹", "whisper_code": "it"},
    "pt": {"name": "Portugais", "emoji": "🇵🇹", "whisper_code": "pt"},
    "ru": {"name": "Russe", "emoji": "🇷🇺", "whisper_code": "ru"},
    "ar": {"name": "Arabe", "emoji": "🇸🇦", "whisper_code": "ar"},
    "hi": {"name": "Hindi", "emoji": "🇮🇳", "whisper_code": "hi"},
    "th": {"name": "Thaï", "emoji": "🇹🇭", "whisper_code": "th"},
    "vi": {"name": "Vietnamien", "emoji": "🇻🇳", "whisper_code": "vi"},
    "id": {"name": "Indonésien", "emoji": "🇮🇩", "whisper_code": "id"},
    "auto": {"name": "Auto-détection", "emoji": "🔍", "whisper_code": None},
}

# Langues cibles pour la traduction
TARGET_LANGUAGES = {
    "fr": {"name": "Français", "emoji": "🇫🇷"},
    "en": {"name": "Anglais", "emoji": "🇬🇧"},
    "es": {"name": "Espagnol", "emoji": "🇪🇸"},
    "de": {"name": "Allemand", "emoji": "🇩🇪"},
    "it": {"name": "Italien", "emoji": "🇮🇹"},
    "pt": {"name": "Portugais", "emoji": "🇵🇹"},
    "zh": {"name": "Chinois simplifié", "emoji": "🇨🇳"},
    "ja": {"name": "Japonais", "emoji": "🇯🇵"},
    "ko": {"name": "Coréen", "emoji": "🇰🇷"},
    "ru": {"name": "Russe", "emoji": "🇷🇺"},
    "ar": {"name": "Arabe", "emoji": "🇸🇦"},
    "hi": {"name": "Hindi", "emoji": "🇮🇳"},
    "nl": {"name": "Néerlandais", "emoji": "🇳🇱"},
    "pl": {"name": "Polonais", "emoji": "🇵🇱"},
    "tr": {"name": "Turc", "emoji": "🇹🇷"},
}


def get_language_display(code: str, languages_dict: dict) -> str:
    """Retourne l'affichage d'une langue (emoji + nom)."""
    if code in languages_dict:
        lang = languages_dict[code]
        return f"{lang['emoji']} {lang['name']}"
    return code


def get_whisper_code(lang_code: str) -> str:
    """Retourne le code Whisper pour une langue donnée."""
    if lang_code in WHISPER_LANGUAGES:
        return WHISPER_LANGUAGES[lang_code].get("whisper_code", lang_code)
    return lang_code


def get_translation_prompt(source_lang: str, target_lang: str) -> str:
    """
    Génère le prompt système pour la traduction.
    
    Args:
        source_lang: Code de la langue source
        target_lang: Code de la langue cible
    
    Returns:
        Le prompt système adapté
    """
    source_name = WHISPER_LANGUAGES.get(source_lang, {}).get("name", source_lang)
    target_name = TARGET_LANGUAGES.get(target_lang, {}).get("name", target_lang)
    
    # Prompts spécialisés selon le type de contenu
    if source_lang == "ja":
        context = "Tu es un expert en traduction de sous-titres d'anime."
    elif source_lang == "ko":
        context = "Tu es un expert en traduction de sous-titres de dramas coréens (K-drama)."
    elif source_lang == "zh":
        context = "Tu es un expert en traduction de sous-titres de dramas chinois (C-drama)."
    else:
        context = "Tu es un expert en traduction de sous-titres de films et séries."
    
    return f"""{context}
Traduis le texte suivant du {source_name} vers le {target_name}.
Règles importantes:
- Garde le ton et le style du dialogue original
- Adapte les expressions idiomatiques naturellement
- Préserve les noms propres et les termes culturels importants
- Réponds uniquement avec la traduction, sans guillemets ni explications."""


def get_source_language_options() -> list:
    """Retourne la liste des options de langue source pour Streamlit."""
    return [
        (code, get_language_display(code, WHISPER_LANGUAGES))
        for code in WHISPER_LANGUAGES.keys()
    ]


def get_target_language_options() -> list:
    """Retourne la liste des options de langue cible pour Streamlit."""
    return [
        (code, get_language_display(code, TARGET_LANGUAGES))
        for code in TARGET_LANGUAGES.keys()
    ]
