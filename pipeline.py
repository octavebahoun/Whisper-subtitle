import subprocess
import sys
import os
from pathlib import Path

def run_step(command):
    print(f"🚀 Exécution : {' '.join(command)}")
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'exécution de {command[1]}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <video_file>")
        sys.exit(1)

    video_file = Path(sys.argv[1])
    if not video_file.exists():
        print(f"❌ Le fichier {video_file} n'existe pas.")
        sys.exit(1)
        
    python_exe = sys.executable

    # 1. Extraction Audio
    print("\n=== Étape 1 : Extraction Audio ===")
    run_step([python_exe, "extract.py", str(video_file)])
    
    audio_file = video_file.with_suffix(".wav")
    
    # 2. Transcription
    print("\n=== Étape 2 : Transcription (Whisper) ===")
    run_step([python_exe, "transcribe.py", str(audio_file)])
    
    srt_file = video_file.with_suffix(".srt")
    
    # 3. Traduction
    print("\n=== Étape 3 : Traduction (Groq) ===")
    run_step([python_exe, "translate.py", str(srt_file)])
    
    srt_fr_file = video_file.with_name(video_file.stem + "_fr.srt")
    output_video = video_file.with_name(video_file.stem + "_vostfr_soft.mp4")

    # 4. Fusion avec FFmpeg
    print(f"\n=== Étape 4 : Fusion des sous-titres dans {output_video} ===")
    # Commande pour incruster les sous-titres en "soft subs" (activables/désactivables)
    # Pour incruster en dur (burn-in), utiliser -vf subtitles=filename
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", str(video_file),
        "-i", str(srt_fr_file),
        "-c", "copy",
        "-c:s", "mov_text",
        "-metadata:s:s:0", "language=fre",
        "-metadata:s:s:0", "title=Français",
        str(output_video)
    ]
    
    try:
        subprocess.run(ffmpeg_cmd, check=True)
        print(f"\n✅ Terminé ! Vidéo disponible : {output_video}")
    except subprocess.CalledProcessError:
        print("❌ Erreur lors de la fusion FFmpeg")

if __name__ == "__main__":
    main()
