"""
Application Streamlit - Générateur automatique de sous-titres.
Supporte plusieurs langues sources et cibles avec cache de traduction.
"""

import streamlit as st
import subprocess
import sys
from pathlib import Path
import shutil
import os

# Import des modules locaux
from languages import (
    WHISPER_LANGUAGES, 
    TARGET_LANGUAGES,
    get_language_display
)
from translation_cache import get_cache_stats, clear_cache

# Configuration de la clé API depuis les secrets Streamlit
if "GROQ_API_KEY" not in st.secrets:
    st.error("❌ Clé API Groq manquante. Configurez GROQ_API_KEY dans les secrets.")
    st.stop()

# Créer un fichier .env temporaire pour les scripts
env_content = f"GROQ_API_KEY={st.secrets['GROQ_API_KEY']}"
with open(".env", "w") as f:
    f.write(env_content)

st.set_page_config(page_title="Auto VOSTFR", page_icon="🎬", layout="wide")

st.title("🎬 Générateur automatique de sous-titres")
st.markdown("**Uploadez une vidéo et obtenez automatiquement une version sous-titrée dans la langue de votre choix**")

# Dossier de travail temporaire
WORK_DIR = Path("uploads")
WORK_DIR.mkdir(exist_ok=True)

# ===== SIDEBAR =====
with st.sidebar:
    st.header("⚙️ Paramètres")
    
    # Sélection des langues
    st.subheader("🌍 Langues")
    
    # Langue source
    source_options = {
        code: f"{info['emoji']} {info['name']}" 
        for code, info in WHISPER_LANGUAGES.items()
    }
    source_lang = st.selectbox(
        "Langue source (audio)",
        options=list(source_options.keys()),
        format_func=lambda x: source_options[x],
        index=list(source_options.keys()).index("ja"),
        help="Langue parlée dans la vidéo"
    )
    
    # Langue cible
    target_options = {
        code: f"{info['emoji']} {info['name']}" 
        for code, info in TARGET_LANGUAGES.items()
    }
    target_lang = st.selectbox(
        "Langue cible (sous-titres)",
        options=list(target_options.keys()),
        format_func=lambda x: target_options[x],
        index=list(target_options.keys()).index("fr"),
        help="Langue des sous-titres générés"
    )
    
    st.divider()
    
    # Mode de transcription
    st.subheader("� Performance")
    fast_mode = st.toggle(
        "Mode Rapide (API)", 
        value=True, 
        help="API Groq = ultra-rapide (recommandé)\nWhisper local = lent sur CPU"
    )
    
    if not fast_mode:
        model_size = st.select_slider(
            "Taille du modèle Whisper",
            options=["tiny", "base", "small", "medium", "large"],
            value="small",
            help="Plus grand = meilleure qualité, mais plus lent"
        )
    else:
        model_size = "small"  # Valeur par défaut (non utilisée en mode API)
    
    st.divider()
    
    # Statistiques du cache
    st.subheader("� Cache de traduction")
    cache_stats = get_cache_stats()
    st.metric("Traductions en cache", cache_stats["total_entries"])
    
    if cache_stats["languages"]:
        st.caption(f"Paires: {', '.join(cache_stats['languages'])}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Vider cache", use_container_width=True):
            clear_cache()
            st.success("Cache vidé !")
            st.rerun()
    
    with col2:
        if st.button("🗑️ Fichiers", use_container_width=True):
            try:
                shutil.rmtree(WORK_DIR)
                WORK_DIR.mkdir(exist_ok=True)
                st.success("Nettoyé !")
            except Exception as e:
                st.error(f"Erreur: {e}")
    
    st.divider()
    
    # Informations
    st.subheader("ℹ️ À propos")
    st.markdown("""
    ### Pipeline
    1. 📤 **Upload** - Importez votre vidéo
    2. 🎵 **Extraction** - Audio extrait (FFmpeg)
    3. 🎤 **Transcription** - Audio → Texte (Whisper)
    4. 🌐 **Traduction** - Texte traduit (Llama 3)
    5. 🎬 **Fusion** - Sous-titres intégrés
    
    ### Technologies
    - **FFmpeg** - Traitement multimédia
    - **Whisper** - Speech-to-text
    - **Groq + Llama 3** - Traduction IA
    - **Streamlit** - Interface web
    """)

# ===== MAIN CONTENT =====
uploaded_file = st.file_uploader(
    "📁 Choisissez une vidéo (MP4, MKV, AVI)", 
    type=["mp4", "mkv", "avi"]
)

if uploaded_file is not None:
    # Sauvegarder le fichier uploadé
    video_path = WORK_DIR / uploaded_file.name
    
    with st.spinner("� Sauvegarde de la vidéo..."):
        with open(video_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    
    source_display = f"{WHISPER_LANGUAGES[source_lang]['emoji']} {WHISPER_LANGUAGES[source_lang]['name']}"
    target_display = f"{TARGET_LANGUAGES[target_lang]['emoji']} {TARGET_LANGUAGES[target_lang]['name']}"
    
    st.success(f"✅ Vidéo chargée : **{uploaded_file.name}**")
    st.info(f"🌐 Traduction : {source_display} → {target_display}")
    
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
            if fast_mode:
                status_text.info(f"🎤 Étape 2/4 : Transcription API ({source_display})...")
                transcribe_cmd = [
                    python_exe, "transcribe_api.py", 
                    str(audio_file),
                    "-l", source_lang
                ]
            else:
                status_text.info(f"🎤 Étape 2/4 : Transcription locale ({source_display}, modèle {model_size})...")
                transcribe_cmd = [
                    python_exe, "transcribe.py", 
                    str(audio_file),
                    "-l", source_lang,
                    "-m", model_size
                ]
            
            progress_bar.progress(30)
            
            result = subprocess.run(
                transcribe_cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                st.error(f"❌ Erreur lors de la transcription:\n{result.stderr}")
                st.stop()
            
            srt_file = video_path.with_suffix(".srt")
            progress_bar.progress(50)
            
            # Étape 3: Traduction
            status_text.info(f"🌐 Étape 3/4 : Traduction → {target_display}...")
            progress_bar.progress(55)
            
            srt_translated = video_path.with_name(f"{video_path.stem}_{target_lang}.srt")
            
            result = subprocess.run(
                [
                    python_exe, "translate.py", 
                    str(srt_file),
                    "-s", source_lang,
                    "-t", target_lang,
                    "-o", str(srt_translated)
                ],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                st.error(f"❌ Erreur lors de la traduction:\n{result.stderr}")
                st.stop()
            
            progress_bar.progress(75)
            
            # Étape 4: Fusion
            status_text.info("🎬 Étape 4/4 : Fusion des sous-titres avec la vidéo...")
            progress_bar.progress(80)
            
            # Mapper le code langue vers le code ISO 639-2 pour FFmpeg
            lang_map = {
                "fr": "fre", "en": "eng", "es": "spa", "de": "ger",
                "it": "ita", "pt": "por", "zh": "chi", "ja": "jpn",
                "ko": "kor", "ru": "rus", "ar": "ara", "hi": "hin",
                "nl": "dut", "pl": "pol", "tr": "tur"
            }
            ffmpeg_lang = lang_map.get(target_lang, "und")
            
            output_video = video_path.with_name(f"{video_path.stem}_vostfr.mp4")
            
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-i", str(srt_translated),
                "-c", "copy",
                "-c:s", "mov_text",
                "-metadata:s:s:0", f"language={ffmpeg_lang}",
                "-metadata:s:s:0", f"title={TARGET_LANGUAGES[target_lang]['name']}",
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
            st.success(f"🎉 Vidéo sous-titrée créée : **{output_video.name}**")
            
            # Statistiques du cache après traduction
            new_stats = get_cache_stats()
            st.info(f"💾 {new_stats['total_entries']} traductions en cache")
            
            col1, col2 = st.columns(2)
            
            # Téléchargement de la vidéo
            with col1:
                with open(output_video, "rb") as f:
                    st.download_button(
                        label="⬇️ Télécharger la vidéo",
                        data=f,
                        file_name=output_video.name,
                        mime="video/mp4",
                        use_container_width=True
                    )
            
            # Téléchargement du SRT
            with col2:
                with open(srt_translated, "r", encoding="utf-8") as f:
                    st.download_button(
                        label="⬇️ Télécharger le fichier SRT",
                        data=f,
                        file_name=srt_translated.name,
                        mime="text/plain",
                        use_container_width=True
                    )
            
            # Aperçu du résultat
            st.subheader("📺 Aperçu de la vidéo sous-titrée")
            st.video(str(output_video))
            
            # Aperçu des sous-titres
            with st.expander("📝 Aperçu des sous-titres (premières lignes)"):
                with open(srt_translated, "r", encoding="utf-8") as f:
                    preview = f.read(2000)
                    st.code(preview, language="")
            
        except Exception as e:
            st.error(f"❌ Une erreur inattendue s'est produite : {str(e)}")
            import traceback
            st.code(traceback.format_exc())

# Footer
st.divider()
st.caption("� **Whisper Subtitle Generator** - Génération automatique de sous-titres avec IA")
