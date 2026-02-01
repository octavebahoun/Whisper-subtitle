"""
Pipeline complet de génération de sous-titres et doublage.
Exécute les étapes en séquence via CLI.
"""

import subprocess
import sys
import argparse
from pathlib import Path

from languages import WHISPER_LANGUAGES, TARGET_LANGUAGES


def run_step(command: list, step_name: str) -> bool:
    """Exécute une étape du pipeline."""
    print(f"🚀 Exécution : {' '.join(command)}")
    try:
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'exécution de {step_name}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline complet de sous-titrage et doublage automatique"
    )
    parser.add_argument("video_file", type=str, help="Fichier vidéo à traiter")
    parser.add_argument(
        "-s", "--source",
        type=str,
        default="ja",
        choices=list(WHISPER_LANGUAGES.keys()),
        help="Langue source de l'audio (défaut: ja)"
    )
    parser.add_argument(
        "-t", "--target",
        type=str,
        default="fr",
        choices=list(TARGET_LANGUAGES.keys()),
        help="Langue cible des sous-titres (défaut: fr)"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        default=True,
        help="Utiliser l'API Groq pour la transcription (défaut: True)"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Utiliser Whisper local pour la transcription"
    )
    parser.add_argument(
        "-m", "--model",
        type=str,
        default="small",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Taille du modèle Whisper local (défaut: small)"
    )
    parser.add_argument(
        "--dub", "--generate",
        action="store_true",
        help="Générer un doublage audio avec TTS"
    )
    parser.add_argument(
        "--ref-audio",
        type=str,
        default=None,
        help="Audio de référence pour le clonage vocal (avec --dub)"
    )
    parser.add_argument(
        "--ref-text",
        type=str,
        default=None,
        help="Texte de l'audio de référence (avec --dub)"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cuda:0", "cuda:1", "cpu"],
        help="Device pour le modèle TTS (défaut: auto)"
    )
    parser.add_argument(
        "--subs-only",
        action="store_true",
        help="Générer uniquement les sous-titres (sans fusion vidéo)"
    )
    
    args = parser.parse_args()
    
    video_file = Path(args.video_file)
    if not video_file.exists():
        print(f"❌ Le fichier {video_file} n'existe pas.")
        sys.exit(1)
    
    python_exe = sys.executable
    source_lang = args.source
    target_lang = args.target
    use_api = not args.local
    
    source_name = WHISPER_LANGUAGES.get(source_lang, {}).get("name", source_lang)
    target_name = TARGET_LANGUAGES.get(target_lang, {}).get("name", target_lang)
    
    print(f"\n{'='*60}")
    print(f"🎬 Pipeline de sous-titrage automatique")
    print(f"{'='*60}")
    print(f"📁 Vidéo: {video_file}")
    print(f"🌍 Traduction: {source_name} → {target_name}")
    print(f"⚡ Mode: {'API Groq (rapide)' if use_api else f'Whisper local ({args.model})'}")
    if args.dub:
        print(f"🎙️ Doublage: Activé (Qwen3-TTS)")
    print(f"{'='*60}\n")

    # 1. Extraction Audio
    print("\n=== Étape 1/4 : Extraction Audio ===")
    if not run_step([python_exe, "extract.py", str(video_file)], "extraction audio"):
        sys.exit(1)
    
    audio_file = video_file.with_suffix(".wav")
    
    # 2. Transcription
    print("\n=== Étape 2/4 : Transcription ===")
    if use_api:
        success = run_step([
            python_exe, "transcribe_api.py", 
            str(audio_file),
            "-l", source_lang
        ], "transcription API")
    else:
        success = run_step([
            python_exe, "transcribe.py", 
            str(audio_file),
            "-l", source_lang,
            "-m", args.model
        ], "transcription locale")
    
    if not success:
        sys.exit(1)
    
    srt_file = video_file.with_suffix(".srt")
    
    # 3. Traduction
    print("\n=== Étape 3/4 : Traduction ===")
    srt_translated = video_file.with_name(f"{video_file.stem}_{target_lang}.srt")
    if not run_step([
        python_exe, "translate.py", 
        str(srt_file),
        "-s", source_lang,
        "-t", target_lang,
        "-o", str(srt_translated)
    ], "traduction"):
        sys.exit(1)
    
    # 4. Génération TTS (optionnel)
    dubbed_audio = None
    if args.dub:
        print("\n=== Étape 4a : Génération Doublage (TTS) ===")
        dubbed_audio = video_file.with_name(f"{video_file.stem}_{target_lang}_dubbed.wav")
        
        dub_cmd = [
            python_exe, "generate.py",
            str(srt_translated),
            "-l", target_lang,
            "-o", str(dubbed_audio),
            "-d", args.device
        ]
        
        if args.ref_audio and args.ref_text:
            dub_cmd.extend(["--ref-audio", args.ref_audio, "--ref-text", args.ref_text])
        
        if not run_step(dub_cmd, "génération TTS"):
            print("⚠️ Échec de la génération TTS, continuation sans doublage")
            dubbed_audio = None
    
    # 5. Fusion avec FFmpeg
    if not args.subs_only:
        print(f"\n=== Étape {'5' if args.dub else '4'}/{'5' if args.dub else '4'} : Fusion Vidéo ===")
        
        # Mapper le code langue vers le code ISO 639-2 pour FFmpeg
        lang_map = {
            "fr": "fre", "en": "eng", "es": "spa", "de": "ger",
            "it": "ita", "pt": "por", "zh": "chi", "ja": "jpn",
            "ko": "kor", "ru": "rus", "ar": "ara", "hi": "hin",
            "nl": "dut", "pl": "pol", "tr": "tur"
        }
        ffmpeg_lang = lang_map.get(target_lang, "und")
        
        if dubbed_audio and dubbed_audio.exists():
            # Fusion avec doublage (remplacer l'audio original)
            output_video = video_file.with_name(f"{video_file.stem}_dubbed.mp4")
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", str(video_file),
                "-i", str(dubbed_audio),
                "-i", str(srt_translated),
                "-map", "0:v:0",           # Vidéo originale
                "-map", "1:a:0",           # Audio doublé
                "-map", "2:0",             # Sous-titres
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-c:s", "mov_text",
                "-metadata:s:s:0", f"language={ffmpeg_lang}",
                "-metadata:s:s:0", f"title={target_name}",
                "-metadata:s:a:0", f"language={ffmpeg_lang}",
                "-metadata:s:a:0", f"title={target_name} (Dubbed)",
                str(output_video)
            ]
        else:
            # Fusion avec sous-titres seulement
            output_video = video_file.with_name(f"{video_file.stem}_vostfr.mp4")
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", str(video_file),
                "-i", str(srt_translated),
                "-c", "copy",
                "-c:s", "mov_text",
                "-metadata:s:s:0", f"language={ffmpeg_lang}",
                "-metadata:s:s:0", f"title={target_name}",
                str(output_video)
            ]
        
        try:
            subprocess.run(ffmpeg_cmd, check=True)
            print(f"\n{'='*60}")
            print(f"✅ Terminé !")
            print(f"📄 Sous-titres : {srt_translated}")
            if dubbed_audio and dubbed_audio.exists():
                print(f"🎙️ Doublage : {dubbed_audio}")
            print(f"🎬 Vidéo : {output_video}")
            print(f"{'='*60}")
        except subprocess.CalledProcessError:
            print("❌ Erreur lors de la fusion FFmpeg")
            sys.exit(1)
    else:
        print(f"\n{'='*60}")
        print(f"✅ Terminé (sous-titres uniquement)")
        print(f"📄 Sous-titres source : {srt_file}")
        print(f"📄 Sous-titres traduits : {srt_translated}")
        if dubbed_audio and dubbed_audio.exists():
            print(f"🎙️ Doublage : {dubbed_audio}")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
