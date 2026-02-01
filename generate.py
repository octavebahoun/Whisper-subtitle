from qwen_tts import Qwen3TTSModel
import soundfile as sf
from pathlib import Path
from tqdm import tqdm

# Chemins
srt_file = Path("jujutsu_kaisen_ep1_fr.srt")
audio_output = Path("jujutsu_kaisen_ep1_fr.wav")

# Charger le modèle 0.6B
model = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-0.6B-Base")

# Collecter tout le texte des sous-titres
texts = []
with open(srt_file, "r", encoding="utf-8") as f:
    block = []
    for line in f:
        line_strip = line.strip()
        if line_strip == "":
            if len(block) >= 3:
                # block[2:] = texte du sous-titre
                text = " ".join(block[2:])
                texts.append(text)
            block = []
        else:
            block.append(line_strip)
    # dernier bloc
    if block and len(block) >= 3:
        texts.append(" ".join(block[2:]))

# Générer audio ligne par ligne et concaténer
all_audio = []
sr = 24000  # sample rate par défaut du modèle
for line in tqdm(texts, desc="Génération audio"):
    wavs, sr_model = model(line)
    sr = sr_model  # récupérer le sample rate
    all_audio.append(wavs)

# Concaténer tous les segments
import numpy as np
final_audio = np.concatenate(all_audio, axis=0)

# Sauvegarder le fichier final
sf.write(audio_output, final_audio, sr)
print("✅ Audio complet généré :", audio_output)
