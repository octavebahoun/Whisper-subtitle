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
        # On utilise -n htdemucs pour être explicite
        subprocess.run(command, check=True)
        
        # Demucs crée un dossier basé sur le nom du modèle (par défaut htdemucs)
        # On cherche récursivement le fichier no_vocals.wav
        base_name = audio_path.stem
        separated_path = Path("separated")
        
        bg_music = None
        for p in separated_path.rglob("no_vocals.wav"):
            if base_name in str(p):
                bg_music = p
                break
        
        if bg_music and bg_music.exists():
            target_bg = audio_path.parent / f"{base_name}_bg.wav"
            shutil.copy(str(bg_music), str(target_bg))
            
            # Nettoyage sécurisé
            if separated_path.exists():
                shutil.rmtree(separated_path)
            
            print(f"✅ Musique de fond extraite : {target_bg}")
            return target_bg
        else:
            print(f"❌ Erreur : Flux no_vocals non trouvé dans {separated_path}")
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
