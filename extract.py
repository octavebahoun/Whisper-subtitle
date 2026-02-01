import subprocess
import sys
from pathlib import Path

# Chemin vers la vidéo (argument ou par défaut)
if len(sys.argv) > 1:
    video_path = Path(sys.argv[1])
else:
    print("Usage: python extract.py <video_file>")
    sys.exit(1)

# Chemin de sortie audio
audio_path = video_path.with_suffix(".wav")

# Commande ffmpeg
command = [
    "ffmpeg",
    "-i", str(video_path),
    "-vn",                # pas de vidéo
    "-acodec", "pcm_s16le",
    "-ar", "16000",       # 16 kHz (idéal pour speech-to-text)
    "-ac", "1",           # mono
    str(audio_path)
]

subprocess.run(command, check=True)

print("✅ Audio extrait avec succès :", audio_path)
