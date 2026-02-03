import re
from pathlib import Path
from typing import List, Dict, Generator, Union

def parse_srt_time(time_str: str) -> float:
    """Convertit un timestamp SRT (HH:MM:SS,mmm) en secondes."""
    # Supporte aussi le format point au lieu de virgule
    match = re.match(r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})', time_str)
    if match:
        h, m, s, ms = map(int, match.groups())
        return h * 3600 + m * 60 + s + ms / 1000
    return 0.0

def format_srt_time(seconds: float) -> str:
    """Convertit les secondes en format SRT (HH:MM:SS,mmm)"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def parse_srt(srt_path: Path) -> List[Dict]:
    """
    Parse un fichier SRT et retourne une liste de segments.
    Chaque segment est un dictionnaire: {'start': float, 'end': float, 'text': str, 'speaker_id': int}
    """
    segments = []
    if not isinstance(srt_path, Path):
        srt_path = Path(srt_path)

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

                    # Détection de speaker ID si présent dans le texte (format: [S1] Texte)
                    speaker_id = 0
                    speaker_match = re.match(r'\[S(\d+)\]\s*(.*)', text)
                    if speaker_match:
                        speaker_id = int(speaker_match.group(1))
                        text = speaker_match.group(2)

                    # Nettoyer les balises HTML/SRT si nécessaire, mais on garde le texte brut généralement
                    # Ici on va juste nettoyer les balises de style basiques pour la synthèse vocale si besoin,
                    # mais pour l'instant on garde tel quel.
                    # Note: generate.py nettoyait les balises <...>. On peut le faire ici.
                    text_clean = re.sub(r'<[^>]+>', '', text)

                    if text_clean:
                        segments.append({
                            'index': lines[0],
                            'start': start,
                            'end': end,
                            'text': text, # On garde le texte original (avec potentielles balises speaker supprimées)
                            'speaker_id': speaker_id
                        })
            except Exception:
                continue
    return segments

def read_srt_blocks(srt_path: Path) -> Generator[List[str], None, None]:
    """
    Générateur qui lit un fichier SRT bloc par bloc.
    Retourne une liste de lignes pour chaque bloc.
    Utile pour le traitement streaming/batch (ex: traduction).
    """
    if not isinstance(srt_path, Path):
        srt_path = Path(srt_path)

    with open(srt_path, "r", encoding="utf-8") as f:
        block = []
        for line in f:
            line_strip = line.strip()
            if line_strip == "":
                if len(block) >= 3:
                    yield block
                block = []
            else:
                block.append(line_strip)

        if block and len(block) >= 3:
            yield block

def write_srt(segments: List[Dict], output_path: Path) -> None:
    """
    Écrit une liste de segments dans un fichier SRT.
    Chaque segment doit avoir 'start', 'end', 'text'.
    """
    if not isinstance(output_path, Path):
        output_path = Path(output_path)

    with open(output_path, "w", encoding="utf-8") as f:
        for i, segment in enumerate(segments, start=1):
            start = format_srt_time(segment['start'])
            end = format_srt_time(segment['end'])
            text = segment['text']

            # Réinsérer le speaker ID si présent et non nul
            if segment.get('speaker_id', 0) > 0:
                 # Vérifier si le tag n'est pas déjà là
                 if not text.startswith(f"[S{segment['speaker_id']}]"):
                     text = f"[S{segment['speaker_id']}] {text}"

            f.write(f"{i}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{text}\n\n")
