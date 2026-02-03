"""
Script de génération de doublage audio à partir de sous-titres SRT.
Utilise edge-tts pour la synthèse vocale et numpy/soundfile pour l'assemblage (compatible Python 3.13+).
"""

import asyncio
import edge_tts
import argparse
import sys
import re
import os
import subprocess
from pathlib import Path
import numpy as np
import soundfile as sf
from tqdm import tqdm

def parse_srt_time(time_str: str) -> float:
    """Convertit un timestamp SRT en secondes."""
    # Format: HH:MM:SS,mmm
    match = re.match(r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})', time_str)
    if match:
        h, m, s, ms = map(int, match.groups())
        return h * 3600 + m * 60 + s + ms / 1000
    return 0.0

def parse_srt(srt_path: Path):
    """Parse un fichier SRT et retourne une liste de segments."""
    segments = []
    if not srt_path.exists():
        return segments

    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Séparer les blocs par double retour à la ligne
    blocks = re.split(r'\n\n+', content.strip())

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            try:
                # Parser les timestamps
                time_match = re.match(
                    r'(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})',
                    lines[1]
                )
                if time_match:
                    start = parse_srt_time(time_match.group(1))
                    end = parse_srt_time(time_match.group(2))
                    text = ' '.join(lines[2:]).strip()
                    # Nettoyer les balises HTML/SRT
                    text = re.sub(r'<[^>]+>', '', text)
                    
                    if text:
                        segments.append({
                            'start': start,
                            'end': end,
                            'text': text
                        })
            except Exception:
                continue
    return segments

async def generate_segment_audio(text: str, speaker: str, output_path: Path):
    """Génère un fichier audio pour un segment de texte et le convertit en WAV."""
    temp_mp3 = output_path.with_suffix(".mp3")
    communicate = edge_tts.Communicate(text, speaker)
    await communicate.save(str(temp_mp3))
    
    # Conversion MP3 -> WAV via FFmpeg (car soundfile lit mieux le WAV)
    subprocess.run([
        "ffmpeg", "-y", "-i", str(temp_mp3), 
        "-ar", "24000", "-ac", "1", str(output_path)
    ], capture_output=True, check=True)
    
    # Nettoyage du MP3 temporaire
    if temp_mp3.exists():
        temp_mp3.unlink()

async def generate_all_segments(segments, speaker, temp_dir):
    """Génère les fichiers audio pour tous les segments en parallèle."""
    temp_dir.mkdir(exist_ok=True)
    semaphore = asyncio.Semaphore(5)

    async def sem_generate(segment, index):
        async with semaphore:
            path = temp_dir / f"seg_{index}.wav"
            await generate_segment_audio(segment['text'], speaker, path)
            return path

    tasks = [sem_generate(seg, i) for i, seg in enumerate(segments)]
    
    paths = []
    # Attendre toutes les tâches et garder l'ordre
    for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="🎙️ Synthèse vocale"):
        await f
    
    return [temp_dir / f"seg_{i}.wav" for i in range(len(segments))]

def assemble_audio(segments, audio_paths, output_path):
    """Assemble les segments audio avec numpy pour éviter la dépendance audioop/pydub."""
    if not audio_paths:
        return

    sample_rate = 24000
    # Durée totale en secondes (dernier segment end + 1s)
    total_duration = segments[-1]['end'] + 1.0
    
    # Créer un array de zéros pour l'audio final
    final_audio = np.zeros(int(total_duration * sample_rate))

    for seg, path in zip(segments, audio_paths):
        if not path.exists():
            continue
            
        try:
            data, sr = sf.read(str(path))
            if sr != sample_rate:
                # On suppose que FFmpeg a bien fait la conversion à 24000
                pass
            
            start_sample = int(seg['start'] * sample_rate)
            end_sample = start_sample + len(data)
            
            if end_sample > len(final_audio):
                # Étendre l'audio si nécessaire
                padding = np.zeros(end_sample - len(final_audio))
                final_audio = np.concatenate([final_audio, padding])
            
            # Superposer l'audio (mixage simple)
            final_audio[start_sample:end_sample] += data
        except Exception as e:
            print(f"⚠️ Erreur sur le segment {path}: {e}")

    # Normalisation pour éviter le clipping
    max_val = np.max(np.abs(final_audio))
    if max_val > 0:
        final_audio = final_audio / max_val * 0.9

    # Sauvegarder le résultat final
    sf.write(str(output_path), final_audio, sample_rate)

async def run_dubbing(srt_file, speaker, output_file):
    srt_path = Path(srt_file)
    output_path = Path(output_file)
    
    print(f"📖 Lecture des sous-titres : {srt_path.name}")
    segments = parse_srt(srt_path)
    if not segments:
        print("❌ Aucun segment trouvé.")
        return

    temp_dir = Path("temp_audio")
    try:
        audio_paths = await generate_all_segments(segments, speaker, temp_dir)
        
        print(f"🔧 Assemblage de l'audio final...")
        assemble_audio(segments, audio_paths, output_path)
        print(f"✅ Terminé ! Audio généré : {output_path}")
    finally:
        # Nettoyage
        for p in temp_dir.glob("*.wav"):
            try: p.unlink()
            except: pass
        if temp_dir.exists():
            try: temp_dir.rmdir()
            except: pass

def main():
    parser = argparse.ArgumentParser(description="Générateur de doublage SRT via Edge-TTS")
    parser.add_argument("srt_file", type=str, help="Fichier SRT")
    parser.add_argument("-s", "--speaker", type=str, default="fr-FR-DeniseNeural", help="Voix Edge-TTS")
    parser.add_argument("-o", "--output", type=str, default="dubbed_audio.wav", help="Fichier de sortie")
    parser.add_argument("-l", "--language", type=str, help="Langue")
    parser.add_argument("-d", "--device", type=str, help="Device")

    args = parser.parse_args()

    asyncio.run(run_dubbing(args.srt_file, args.speaker, args.output))

if __name__ == "__main__":
    main()

