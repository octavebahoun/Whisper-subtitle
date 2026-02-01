"""
Script de transcription via l'API Groq Whisper.
Supporte plusieurs langues sources avec chunking pour les longs fichiers.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
import time

from languages import WHISPER_LANGUAGES, get_whisper_code

# Charger les variables d'environnement
load_dotenv()

# Récupération de la clé API
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("❌ Erreur : La clé GROQ_API_KEY est introuvable dans le fichier .env")
    sys.exit(1)

# Configuration du client Groq avec timeout augmenté
client = Groq(
    api_key=api_key,
    timeout=300.0  # 5 minutes timeout
)

# Mots/phrases typiques des hallucinations Whisper
HALLUCINATION_PATTERNS = [
    "ご視聴ありがとうございました",
    "チャンネル登録",
    "いいねボタン",
    "thanks for watching",
    "please subscribe",
    "like and subscribe",
    "merci d'avoir regardé",
    "abonnez-vous",
]


def format_time(seconds: float) -> str:
    """Convertit les secondes en format SRT (HH:MM:SS,mmm)"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def get_audio_duration(audio_path: Path) -> float:
    """Obtient la durée de l'audio en secondes."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
        capture_output=True, text=True
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0


def is_hallucination(text: str, all_texts: list) -> bool:
    """Détecte si un texte est probablement une hallucination."""
    text_lower = text.lower().strip()
    
    if len(text_lower) < 3:
        return True
    
    for pattern in HALLUCINATION_PATTERNS:
        if pattern.lower() in text_lower:
            return True
    
    count = sum(1 for t in all_texts if t.strip() == text.strip())
    if count > 2:
        return True
    
    return False


def compress_audio_chunk(audio_path: Path, output_path: Path, start: float, duration: float) -> Path:
    """
    Extrait et compresse un segment audio.
    
    Args:
        audio_path: Fichier audio source
        output_path: Chemin de sortie
        start: Début du segment en secondes
        duration: Durée du segment en secondes
    """
    command = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", str(audio_path),
        "-t", str(duration),
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        "-b:a", "64k",
        str(output_path)
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path


def transcribe_chunk(chunk_path: Path, language: str, chunk_index: int, total_chunks: int) -> dict:
    """
    Transcrit un seul chunk audio.
    
    Returns:
        dict avec 'segments' (liste) et 'language' (détectée)
    """
    whisper_code = get_whisper_code(language)
    
    print(f"   📦 Chunk {chunk_index}/{total_chunks}: {chunk_path.stat().st_size / 1024:.0f} KB")
    
    with open(chunk_path, "rb") as audio_file:
        api_kwargs = {
            "file": (chunk_path.name, audio_file.read()),
            "model": "whisper-large-v3-turbo",
            "response_format": "verbose_json",
        }
        
        if whisper_code:
            api_kwargs["language"] = whisper_code
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                transcription = client.audio.transcriptions.create(**api_kwargs)
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"   ⚠️ Retry {attempt + 1}/{max_retries}...")
                    time.sleep(2)
                else:
                    raise e
    
    segments = []
    if hasattr(transcription, 'segments') and transcription.segments:
        segments = transcription.segments
    elif hasattr(transcription, 'text') and transcription.text:
        segments = [{'start': 0, 'end': 10, 'text': transcription.text}]
    
    detected_lang = getattr(transcription, 'language', None)
    
    return {'segments': segments, 'language': detected_lang}


def transcribe_with_api(audio_path: Path, language: str = "ja") -> Path:
    """
    Transcription via l'API Groq Whisper avec chunking automatique.
    
    Args:
        audio_path: Chemin vers le fichier audio
        language: Code de la langue source (défaut: "ja")
    
    Returns:
        Chemin vers le fichier SRT généré
    """
    whisper_code = get_whisper_code(language)
    lang_name = WHISPER_LANGUAGES.get(language, {}).get("name", language)
    
    print(f"🚀 Transcription via API Groq")
    print(f"🌍 Langue: {lang_name} ({whisper_code or 'auto'})")
    print(f"📁 Fichier: {audio_path}")
    
    # Obtenir la durée
    duration = get_audio_duration(audio_path)
    print(f"⏱️ Durée: {duration:.1f}s ({duration/60:.1f} min)")
    
    # Vérifier la taille
    original_size_mb = audio_path.stat().st_size / (1024 * 1024)
    print(f"📊 Taille: {original_size_mb:.1f} MB")
    
    # Calculer le chunking
    # Groq limite à ~25 MB, on vise 5-6 MB par chunk pour être safe
    # À 64kbps : 5 MB = ~10 minutes d'audio
    CHUNK_DURATION = 600  # 10 minutes par chunk
    MAX_CHUNK_SIZE_MB = 20  # Limite safe
    
    try:
        all_segments = []
        time_offset = 0.0
        temp_files = []
        
        if duration <= CHUNK_DURATION:
            # Un seul chunk
            print("📦 Fichier court, pas de chunking nécessaire")
            
            # Compresser
            compressed = audio_path.with_suffix(".mp3")
            compress_audio_chunk(audio_path, compressed, 0, duration)
            temp_files.append(compressed)
            
            file_size = compressed.stat().st_size / (1024 * 1024)
            print(f"📊 Taille compressée: {file_size:.1f} MB")
            
            if file_size > MAX_CHUNK_SIZE_MB:
                print("❌ Fichier trop volumineux pour l'API")
                print("💡 Utilisez le mode local (Whisper) pour les longs fichiers")
                for f in temp_files:
                    if f.exists():
                        f.unlink()
                sys.exit(1)
            
            print("🔄 Transcription en cours...")
            result = transcribe_chunk(compressed, language, 1, 1)
            all_segments = list(result.get('segments', []))
            
            if result.get('language'):
                print(f"🔍 Langue détectée: {result['language']}")
        
        else:
            # Multi-chunks
            num_chunks = int(duration // CHUNK_DURATION) + 1
            print(f"📂 Découpage en {num_chunks} chunks de {CHUNK_DURATION//60} min")
            
            for i in range(num_chunks):
                chunk_start = i * CHUNK_DURATION
                chunk_dur = min(CHUNK_DURATION, duration - chunk_start)
                
                if chunk_dur < 1:
                    continue
                
                # Créer le chunk compressé
                chunk_path = audio_path.with_name(f"{audio_path.stem}_chunk{i+1}.mp3")
                compress_audio_chunk(audio_path, chunk_path, chunk_start, chunk_dur)
                temp_files.append(chunk_path)
                
                # Transcrire
                print(f"🔄 Transcription chunk {i+1}/{num_chunks} ({chunk_start//60:.0f}-{(chunk_start+chunk_dur)//60:.0f} min)...")
                result = transcribe_chunk(chunk_path, language, i+1, num_chunks)
                
                # Ajouter les segments avec offset temporel
                for seg in result.get('segments', []):
                    adjusted_seg = {
                        'start': seg.get('start', 0) + chunk_start,
                        'end': seg.get('end', 0) + chunk_start,
                        'text': seg.get('text', '')
                    }
                    all_segments.append(adjusted_seg)
                
                # Petit délai entre les chunks pour éviter le rate limiting
                if i < num_chunks - 1:
                    time.sleep(1)
        
        # Nettoyer les fichiers temporaires
        for f in temp_files:
            if f.exists():
                f.unlink()
        
        # Collecter tous les textes pour la détection d'hallucinations
        all_texts = [seg.get('text', '').strip() for seg in all_segments]
        
        # Créer le fichier SRT
        srt_path = audio_path.with_suffix(".srt")
        valid_segments = 0
        hallucination_count = 0
        
        with open(srt_path, "w", encoding="utf-8") as f:
            segment_index = 1
            for segment in all_segments:
                start = segment.get('start', 0)
                end = segment.get('end', 0)
                text = segment.get('text', '').strip()
                
                if is_hallucination(text, all_texts):
                    hallucination_count += 1
                    continue
                
                f.write(f"{segment_index}\n")
                f.write(f"{format_time(start)} --> {format_time(end)}\n")
                f.write(f"{text}\n\n")
                segment_index += 1
                valid_segments += 1
        
        if hallucination_count > 0:
            print(f"🔍 {hallucination_count} hallucinations filtrées")
        
        print(f"✅ {valid_segments} segments → {srt_path}")
        
        # Aperçu
        with open(srt_path, "r", encoding="utf-8") as f:
            preview = f.read(600)
            if preview.strip():
                print(f"\n📄 Aperçu:\n{preview}")
        
        return srt_path
        
    except Exception as e:
        # Nettoyer en cas d'erreur
        for f in temp_files if 'temp_files' in dir() else []:
            if f.exists():
                f.unlink()
        
        print(f"❌ Erreur lors de la transcription: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Transcription audio via API Groq Whisper"
    )
    parser.add_argument("audio_file", type=str, help="Fichier audio à transcrire")
    parser.add_argument(
        "-l", "--language",
        type=str,
        default="ja",
        choices=list(WHISPER_LANGUAGES.keys()),
        help="Langue source de l'audio (défaut: ja, ou 'auto' pour auto-détection)"
    )
    
    args = parser.parse_args()
    
    audio_path = Path(args.audio_file)
    
    if not audio_path.exists():
        print(f"❌ Fichier introuvable: {audio_path}")
        sys.exit(1)
    
    transcribe_with_api(audio_path, args.language)


if __name__ == "__main__":
    main()
