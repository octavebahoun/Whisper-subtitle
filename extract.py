import subprocess
from pathlib import Path

# Chemin vers la vidéo
video_path = Path("jujutsu_kaisen_ep2.mp4")

# Chemin de sortie audio
audio_path = Path("jujutsu_kaisen_ep2.wav")

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
