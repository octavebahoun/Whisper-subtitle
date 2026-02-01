import whisper
from pathlib import Path

# Charger le modèle
model = whisper.load_model("small")

# Chemin vers l'audio
audio_path = Path("jujutsu_kaisen_ep1.wav")

# Transcription (japonais, sans traduction)
result = model.transcribe(
    str(audio_path),
    language="ja",
    task="transcribe"
)

# Sauvegarde du SRT
srt_path = audio_path.with_suffix(".srt")

with open(srt_path, "w", encoding="utf-8") as f:
    for i, segment in enumerate(result["segments"], start=1):
        start = segment["start"]
        end = segment["end"]
        text = segment["text"].strip()

        def format_time(t):
            h = int(t // 3600)
            m = int((t % 3600) // 60)
            s = int(t % 60)
            ms = int((t - int(t)) * 1000)
            return f"{h:02}:{m:02}:{s:02},{ms:03}"

        f.write(f"{i}\n")
        f.write(f"{format_time(start)} --> {format_time(end)}\n")
        f.write(text + "\n\n")

print("✅ Sous-titres japonais générés :", srt_path)
