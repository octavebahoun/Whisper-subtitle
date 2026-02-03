import subprocess
import sys
from pathlib import Path
import os
import shutil

def separate_audio(audio_path: Path):
    """
    Sépare les voix de la musique de fond en utilisant Demucs.
    """
    print(f"🎵 Séparation de l'audio : {audio_path}")
    
    # Commande demucs : --two-stems=vocals sépare en voix et accompagnement
    # -d cpu pour s'assurer que ça passe partout
    command = [
        "demucs",
        "--two-stems", "vocals",
        "-d", "cpu",
        str(audio_path)
    ]
    
    try:
        subprocess.run(command, check=True)
        
        # Demucs crée par défaut un dossier 'separated/htdemucs/nom_du_fichier/'
        # On doit récupérer le fichier 'no_vocals.wav' (qui est l'accompagnement)
        base_name = audio_path.stem
        output_dir = Path("separated/htdemucs") / base_name
        
        bg_music = output_dir / "no_vocals.wav"
        vocals = output_dir / "vocals.wav"
        
        if bg_music.exists():
            # On déplace l'accompagnement vers un nom plus clair dans le dossier uploads
            target_bg = audio_path.parent / f"{base_name}_bg.wav"
            shutil.move(str(bg_music), str(target_bg))
            
            # Nettoyage
            shutil.rmtree("separated")
            
            print(f"✅ Musique de fond extraite : {target_bg}")
            return target_bg
        else:
            print("❌ Erreur : Fichiers séparés non trouvés")
            return None
            
    except Exception as e:
        print(f"❌ Erreur lors de la séparation : {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        audio_file = Path(sys.argv[1])
        separate_audio(audio_file)
    else:
        print("Usage: python separate.py <audio_file>")
