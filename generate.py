"""
Script de génération de doublage audio à partir de sous-titres SRT.
Utilise edge-tts pour la synthèse vocale et pydub pour l'assemblage.
"""

import asyncio
import edge_tts
import argparse
import sys
import re
import os
from pathlib import Path
from pydub import AudioSegment
from tqdm import tqdm

def parse_srt_time(time_str: str) -> int:
    """Convertit un timestamp SRT en millisecondes."""
    # Format: HH:MM:SS,mmm
    match = re.match(r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})', time_str)
    if match:
        h, m, s, ms = map(int, match.groups())
        return (h * 3600 + m * 60 + s) * 1000 + ms
    return 0

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

async def generate_segment_mp3(text: str, speaker: str, output_path: str):
    """Génère un fichier MP3 pour un segment de texte."""
    communicate = edge_tts.Communicate(text, speaker)
    await communicate.save(output_path)

async def generate_all_segments(segments, speaker, temp_dir):
    """Génère les fichiers audio pour tous les segments en parallèle (avec limite)."""
    tasks = []
    # Créer le dossier temp si besoin
    temp_dir.mkdir(exist_ok=True)
    
    semaphore = asyncio.Semaphore(5) # Limiter le nombre de requêtes simultanées

    async def sem_generate(segment, index):
        async with semaphore:
            path = temp_dir / f"seg_{index}.mp3"
            await generate_segment_mp3(segment['text'], speaker, str(path))
            return path

    for i, seg in enumerate(segments):
        tasks.append(sem_generate(seg, i))
    
    # Utiliser tqdm pour suivre la progression
    paths = []
    for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="🎙️ Synthèse vocale"):
        paths.append(await f)
    
    # Il faut les trier car as_completed ne garantit pas l'ordre
    # On reconstruit la liste triée par index
    return [temp_dir / f"seg_{i}.mp3" for i in range(len(segments))]

def assemble_audio(segments, audio_paths, output_path):
    """Assemble les segments audio en respectant les timestamps."""
    if not audio_paths:
        return

    # Durée totale estimée (dernier segment end + 1s)
    total_duration = segments[-1]['end'] + 1000
    
    # Créer une piste de silence
    combined = AudioSegment.silent(duration=total_duration)

    for seg, path in zip(segments, audio_paths):
        if not path.exists():
            continue
            
        try:
            segment_audio = AudioSegment.from_file(path)
            # Positionner le segment à son timestamp de début
            # Overlay permet de superposer au silence
            combined = combined.overlay(segment_audio, position=seg['start'])
        except Exception as e:
            print(f"⚠️ Erreur sur le segment {path}: {e}")

    # Sauvegarder le résultat final
    combined.export(output_path, format="wav")

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
        # Nettoyage des fichiers temporaires
        for p in temp_dir.glob("*.mp3"):
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
