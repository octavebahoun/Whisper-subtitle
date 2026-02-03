import sys
import json
from pathlib import Path
import subprocess

def run_diarization(audio_path: Path, num_speakers=None):
    """
    Identifie les différents locuteurs dans un fichier audio.
    Retourne une liste de segments avec l'ID du locuteur.
    """
    print(f"🕵️ Diarisation de l'audio : {audio_path}", file=sys.stderr)
    
    # Pour une implémentation simplifiée et robuste sans dépendances complexes (pyannote),
    # on va utiliser simple-diarizer ou un mockup si l'installation échoue.
    # En production, on utiliserait pyannote/speaker-diarization
    
    try:
        from simple_diarizer.diarizer import Diarizer
        
        # Initialiser le diariseur
        diarizer = Diarizer(
            embed_model='xvec', # ou 'resnet'
            cluster_method='ahc'
        )
        
        # Effectuer la diarisation
        if num_speakers is not None:
            segments = diarizer.diarize(str(audio_path), num_speakers=int(num_speakers))
        else:
            segments = diarizer.diarize(str(audio_path))
        
        # On convertit le format pour notre usage
        # Format attendu : [{"start": 0.0, "end": 2.0, "speaker": 1}, ...]
        formatted_segments = []
        for seg in segments:
            formatted_segments.append({
                "start": float(seg[0]),
                "end": float(seg[1]),
                "speaker": int(seg[2])
            })
            
        print(f"✅ Diarisation terminée : {len(formatted_segments)} segments identifiés", file=sys.stderr)
        return formatted_segments

    except ImportError:
        print("❌ Erreur : Module 'simple_diarizer' manquant.", file=sys.stderr)
        print("ℹ️  Installez-le avec : pip install simple-diarizer", file=sys.stderr)
        return []
        
    except Exception as e:
        print(f"⚠️ Erreur Diarisation : {e}", file=sys.stderr)
        # Mockup pour le test : tout est attribué au Speaker 0
        return []

def assign_speakers_to_srt(srt_segments, diarization_segments):
    """
    Assigne un Speaker ID à chaque segment de sous-titre SRT
    en se basant sur les timestamps de la diarisation.
    """
    if not diarization_segments:
        for seg in srt_segments:
            seg['speaker'] = 0
        return srt_segments

    for srt_seg in srt_segments:
        srt_mid = (srt_seg['start'] + srt_seg['end']) / 2 / 1000 # ms to s
        
        # Trouver le segment de diarisation qui contient le milieu du sous-titre
        assigned_speaker = 0
        for d_seg in diarization_segments:
            if d_seg['start'] <= srt_mid <= d_seg['end']:
                assigned_speaker = d_seg['speaker']
                break
        
        srt_seg['speaker'] = assigned_speaker
        
    return srt_segments

if __name__ == "__main__":
    if len(sys.argv) > 1:
        audio_file = Path(sys.argv[1])
        res = run_diarization(audio_file)
        print(json.dumps(res))
    else:
        print("Usage: python diarize.py <audio_file>")
