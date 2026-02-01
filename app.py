import streamlit as st
import subprocess
import sys
from pathlib import Path
import shutil
import tempfile
import os

# Configuration de la clé API depuis les secrets Streamlit
if "GROQ_API_KEY" not in st.secrets:
    st.error("❌ Clé API Groq manquante. Configurez GROQ_API_KEY dans les secrets.")
    st.stop()

# Créer un fichier .env temporaire pour les scripts
env_content = f"GROQ_API_KEY={st.secrets['GROQ_API_KEY']}"
with open(".env", "w") as f:
    f.write(env_content)

st.set_page_config(page_title="Auto VOSTFR", page_icon="🎬", layout="wide")

st.title("🎬 Générateur automatique de sous-titres français")
st.markdown("**Uploadez une vidéo d'anime en japonais et obtenez automatiquement une version avec sous-titres français**")

# Dossier de travail temporaire
WORK_DIR = Path("uploads")
WORK_DIR.mkdir(exist_ok=True)

uploaded_file = st.file_uploader(
    "📁 Choisissez une vidéo (MP4, MKV, AVI)", 
    type=["mp4", "mkv", "avi"]
)

if uploaded_file is not None:
    # Sauvegarder le fichier uploadé
    video_path = WORK_DIR / uploaded_file.name
    
    with st.spinner("📥 Sauvegarde de la vidéo..."):
        with open(video_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    
    st.success(f"✅ Vidéo chargée : {uploaded_file.name}")
    
    # Afficher un aperçu de la vidéo
    with st.expander("👁️ Aperçu de la vidéo"):
        st.video(str(video_path))
    
    # Bouton de traitement
    if st.button("🚀 Lancer le traitement automatique", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        python_exe = sys.executable
        
        try:
            # Étape 1: Extraction audio
            status_text.info("🎵 Étape 1/4 : Extraction de l'audio...")
            progress_bar.progress(10)
            
            result = subprocess.run(
                [python_exe, "extract.py", str(video_path)],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                st.error(f"❌ Erreur lors de l'extraction audio:\n{result.stderr}")
                st.stop()
            
            audio_file = video_path.with_suffix(".wav")
            progress_bar.progress(25)
            
            # Étape 2: Transcription
            status_text.info("🎤 Étape 2/4 : Transcription avec Whisper (cela peut prendre plusieurs minutes)...")
            progress_bar.progress(30)
            
            result = subprocess.run(
                [python_exe, "transcribe.py", str(audio_file)],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                st.error(f"❌ Erreur lors de la transcription:\n{result.stderr}")
                st.stop()
            
            srt_file = video_path.with_suffix(".srt")
            progress_bar.progress(50)
            
            # Étape 3: Traduction
            status_text.info("🌐 Étape 3/4 : Traduction en français avec Llama 3...")
            progress_bar.progress(55)
            
            result = subprocess.run(
                [python_exe, "translate.py", str(srt_file)],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                st.error(f"❌ Erreur lors de la traduction:\n{result.stderr}")
                st.stop()
            
            srt_fr_file = video_path.with_name(video_path.stem + "_fr.srt")
            progress_bar.progress(75)
            
            # Étape 4: Fusion
            status_text.info("🎬 Étape 4/4 : Fusion des sous-titres avec la vidéo...")
            progress_bar.progress(80)
            
            output_video = video_path.with_name(video_path.stem + "_vostfr.mp4")
            
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-i", str(srt_fr_file),
                "-c", "copy",
                "-c:s", "mov_text",
                "-metadata:s:s:0", "language=fre",
                "-metadata:s:s:0", "title=Français",
                str(output_video)
            ]
            
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                st.error(f"❌ Erreur lors de la fusion FFmpeg:\n{result.stderr}")
                st.stop()
            
            progress_bar.progress(100)
            status_text.success("✅ Traitement terminé avec succès !")
            
            # Afficher les résultats
            st.success(f"🎉 Vidéo VOSTFR créée : {output_video.name}")
            
            col1, col2 = st.columns(2)
            
            # Téléchargement de la vidéo
            with col1:
                with open(output_video, "rb") as f:
                    st.download_button(
                        label="⬇️ Télécharger la vidéo VOSTFR",
                        data=f,
                        file_name=output_video.name,
                        mime="video/mp4",
                        use_container_width=True
                    )
            
            # Téléchargement du SRT
            with col2:
                with open(srt_fr_file, "r", encoding="utf-8") as f:
                    st.download_button(
                        label="⬇️ Télécharger le fichier SRT",
                        data=f,
                        file_name=srt_fr_file.name,
                        mime="text/plain",
                        use_container_width=True
                    )
            
            # Aperçu du résultat
            st.subheader("📺 Aperçu de la vidéo VOSTFR")
            st.video(str(output_video))
            
            # Aperçu des sous-titres
            with st.expander("📝 Aperçu des sous-titres (premières lignes)"):
                with open(srt_fr_file, "r", encoding="utf-8") as f:
                    preview = f.read(1000)
                    st.code(preview, language="")
            
        except Exception as e:
            st.error(f"❌ Une erreur inattendue s'est produite : {str(e)}")
            import traceback
            st.code(traceback.format_exc())

# Sidebar avec informations
with st.sidebar:
    st.header("ℹ️ Informations")
    st.markdown("""
    ### Comment ça marche ?
    
    1. **📤 Upload** : Importez votre vidéo d'anime
    2. **🎵 Extraction** : L'audio est extrait
    3. **🎤 Transcription** : Whisper transcrit en japonais
    4. **🌐 Traduction** : Llama 3 traduit en français
    5. **🎬 Fusion** : Les sous-titres sont ajoutés à la vidéo
    
    ### ⚙️ Technologies utilisées
    - **FFmpeg** : Extraction audio et fusion
    - **Whisper** : Transcription audio → texte
    - **Groq (Llama 3)** : Traduction JA → FR
    - **Streamlit** : Interface web
    
    ### ⚠️ Notes
    - Le traitement peut prendre plusieurs minutes
    - La transcription est plus rapide avec un GPU
    - Les fichiers sont sauvegardés dans `uploads/`
    """)
    
    # Nettoyage
    st.divider()
    if st.button("🗑️ Nettoyer les fichiers temporaires"):
        try:
            shutil.rmtree(WORK_DIR)
            WORK_DIR.mkdir(exist_ok=True)
            st.success("✅ Fichiers nettoyés")
        except Exception as e:
            st.error(f"Erreur : {e}")
