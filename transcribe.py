"""
Script de transcription locale avec Whisper.
Supporte plusieurs langues sources.
"""

import whisper
import sys
import argparse
from pathlib import Path

from languages import WHISPER_LANGUAGES, get_whisper_code
import srt_utils


def transcribe_local(audio_path: Path, language: str = "ja", model_size: str = "small") -> Path:
    """
    Transcription locale avec Whisper.
    
    Args:
        audio_path: Chemin vers le fichier audio
        language: Code de la langue source (défaut: "ja")
        model_size: Taille du modèle Whisper (tiny, base, small, medium, large)
    
    Returns:
        Chemin vers le fichier SRT généré
    """
    whisper_code = get_whisper_code(language)
    lang_name = WHISPER_LANGUAGES.get(language, {}).get("name", language)
    
    print(f"🎤 Transcription locale avec Whisper")
    print(f"🌍 Langue: {lang_name} ({whisper_code or 'auto'})")
    print(f"📦 Modèle: {model_size}")
    print(f"📁 Fichier: {audio_path}")
    
    # Charger le modèle
    print(f"⏳ Chargement du modèle Whisper ({model_size})...")
    model = whisper.load_model(model_size)
    
    # Préparer les arguments de transcription
    transcribe_kwargs = {
        "task": "transcribe"
    }
    
    # Ajouter la langue seulement si ce n'est pas "auto"
    if whisper_code:
        transcribe_kwargs["language"] = whisper_code
    
    # Transcription
    print("🔄 Transcription en cours (cela peut prendre plusieurs minutes)...")
    result = model.transcribe(str(audio_path), **transcribe_kwargs)
    
    # Afficher la langue détectée si auto-détection
    if not whisper_code:
        detected = result.get("language", "inconnu")
        print(f"🔍 Langue détectée: {detected}")
    
    # Sauvegarde du SRT
    srt_path = audio_path.with_suffix(".srt")
    
    srt_segments = []
    for segment in result["segments"]:
        srt_segments.append({
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"].strip()
        })

    srt_utils.write_srt(srt_segments, srt_path)
    
    print(f"✅ Sous-titres générés : {srt_path}")
    return srt_path


def main():
    parser = argparse.ArgumentParser(
        description="Transcription audio avec Whisper local"
    )
    parser.add_argument("audio_file", type=str, help="Fichier audio à transcrire")
    parser.add_argument(
        "-l", "--language",
        type=str,
        default="ja",
        choices=list(WHISPER_LANGUAGES.keys()),
        help="Langue source de l'audio (défaut: ja, ou 'auto' pour auto-détection)"
    )
    parser.add_argument(
        "-m", "--model",
        type=str,
        default="small",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Taille du modèle Whisper (défaut: small)"
    )
    
    args = parser.parse_args()
    
    audio_path = Path(args.audio_file)
    
    if not audio_path.exists():
        print(f"❌ Fichier introuvable: {audio_path}")
        sys.exit(1)
    
    transcribe_local(audio_path, args.language, args.model)


if __name__ == "__main__":
    main()
