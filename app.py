"""
Application Streamlit - Générateur automatique de sous-titres et doublage.
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

# Langues supportées par Qwen3-TTS
TTS_LANGUAGES = ["fr", "en", "ja", "zh", "ko", "de", "es", "it", "pt", "ru"]

# Speakers disponibles pour Edge-TTS
TTS_SPEAKERS = {
    # Français
    "fr-FR-DeniseNeural": {"gender": "female", "native": "Français", "label": "Denise (FR)"},
    "fr-FR-HenriNeural": {"gender": "male", "native": "Français", "label": "Henri (FR)"},
    "fr-FR-EloiseNeural": {"gender": "female", "native": "Français", "label": "Eloise (FR)"},
    # Anglais
    "en-US-AriaNeural": {"gender": "female", "native": "Anglais", "label": "Aria (US)"},
    "en-US-GuyNeural": {"gender": "male", "native": "Anglais", "label": "Guy (US)"},
    "en-US-JennyNeural": {"gender": "female", "native": "Anglais", "label": "Jenny (US)"},
    # Japonais
    "ja-JP-NanamiNeural": {"gender": "female", "native": "Japonais", "label": "Nanami (JP)"},
    "ja-JP-KeitaNeural": {"gender": "male", "native": "Japonais", "label": "Keita (JP)"},
}

# Configuration de la clé API depuis les secrets Streamlit
if "GROQ_API_KEY" not in st.secrets:
    st.error("❌ Clé API Groq manquante. Configurez GROQ_API_KEY dans les secrets.")
    st.stop()

# Créer un fichier .env temporaire pour les scripts
env_content = f"GROQ_API_KEY={st.secrets['GROQ_API_KEY']}"
with open(".env", "w") as f:
    f.write(env_content)

st.set_page_config(page_title="Auto VOSTFR + Doublage", page_icon="🎬", layout="wide")

st.title("🎬 Générateur de sous-titres & doublage IA")
st.markdown("**Uploadez une vidéo et obtenez automatiquement des sous-titres traduits et/ou un doublage IA**")

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
    st.subheader("🚀 Transcription")
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
        model_size = "small"
    
    st.divider()
    
    # Option Doublage TTS
    st.subheader("🎙️ Doublage IA")
    
    # Vérifier si la langue cible supporte le TTS
    tts_available = target_lang in TTS_LANGUAGES
    
    if tts_available:
        enable_tts = st.toggle(
            "Générer le doublage",
            value=False,
            help="Génère un audio doublé avec Qwen3-TTS (lent sur CPU)"
        )
        
        if enable_tts:
            st.info("⚠️ Le doublage peut prendre plusieurs minutes sur CPU")
            
            # Sélection du type de voix
            st.markdown("**Type de voix**")
            
            # Séparer les voix par genre
            female_voices = [name for name, info in TTS_SPEAKERS.items() if info["gender"] == "female"]
            male_voices = [name for name, info in TTS_SPEAKERS.items() if info["gender"] == "male"]
            
            gender = st.radio(
                "Genre",
                options=["Féminin", "Masculin"],
                horizontal=True,
                label_visibility="collapsed"
            )
            
            if gender == "Féminin":
                available_speakers = female_voices
                default_speaker = "fr-FR-DeniseNeural"
            else:
                available_speakers = male_voices
                default_speaker = "fr-FR-HenriNeural"
            
            # Formater les options avec label
            speaker_options = {
                name: TTS_SPEAKERS[name]['label']
                for name in available_speakers
            }
            
            selected_speaker = st.selectbox(
                "Voix",
                options=list(speaker_options.keys()),
                format_func=lambda x: speaker_options[x],
                index=list(speaker_options.keys()).index(default_speaker) if default_speaker in speaker_options else 0,
                help="Choisissez la voix pour le doublage"
            )
            
            # Option clonage vocal
            use_voice_clone = st.toggle(
                "Clonage vocal (expérimental)",
                value=False,
                help="Utiliser un audio de référence pour cloner une voix"
            )
            
            if use_voice_clone:
                ref_audio_file = st.file_uploader(
                    "Audio de référence (WAV)",
                    type=["wav", "mp3"],
                    help="Audio de 3-10 secondes de la voix à cloner"
                )
                ref_text = st.text_area(
                    "Texte prononcé dans l'audio",
                    placeholder="Entrez le texte exact prononcé dans l'audio de référence...",
                    height=100
                )
            else:
                ref_audio_file = None
                ref_text = None
        else:
            selected_speaker = "Chelsie"
            use_voice_clone = False
            ref_audio_file = None
            ref_text = None
    else:
        enable_tts = False
        selected_speaker = "Chelsie"
        use_voice_clone = False
        ref_audio_file = None
        ref_text = None
        st.warning(f"⚠️ TTS non disponible pour {TARGET_LANGUAGES[target_lang]['name']}")
        st.caption(f"Langues TTS: {', '.join(TTS_LANGUAGES)}")
    
    st.divider()
    
    # Statistiques du cache
    st.subheader("💾 Cache")
    cache_stats = get_cache_stats()
    st.metric("Traductions en cache", cache_stats["total_entries"])
    
    if cache_stats["languages"]:
        st.caption(f"Paires: {', '.join(cache_stats['languages'])}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Cache", use_container_width=True):
            clear_cache()
            st.success("Vidé !")
            st.rerun()
    
    with col2:
        if st.button("🗑️ Fichiers", use_container_width=True):
            try:
                shutil.rmtree(WORK_DIR)
                WORK_DIR.mkdir(exist_ok=True)
                st.success("Nettoyé !")
            except Exception as e:
                st.error(f"Erreur: {e}")

# ===== MAIN CONTENT =====
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
    
    source_display = f"{WHISPER_LANGUAGES[source_lang]['emoji']} {WHISPER_LANGUAGES[source_lang]['name']}"
    target_display = f"{TARGET_LANGUAGES[target_lang]['emoji']} {TARGET_LANGUAGES[target_lang]['name']}"
    
    st.success(f"✅ Vidéo chargée : **{uploaded_file.name}**")
    
    # Afficher les paramètres sélectionnés
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"🌐 {source_display} → {target_display}")
    with col2:
        st.info(f"⚡ {'API Groq' if fast_mode else f'Whisper {model_size}'}")
    with col3:
        if enable_tts:
            gender_emoji = "👩" if TTS_SPEAKERS[selected_speaker]["gender"] == "female" else "👨"
            st.info(f"🎙️ Doublage: {gender_emoji} {selected_speaker}")
        else:
            st.info("📝 Sous-titres uniquement")
    
    # Afficher un aperçu de la vidéo
    with st.expander("👁️ Aperçu de la vidéo"):
        st.video(str(video_path))
    
    # Calculer le nombre d'étapes
    total_steps = 5 if enable_tts else 4
    
    # Bouton de traitement
    if st.button("🚀 Lancer le traitement automatique", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        python_exe = sys.executable
        
        try:
            # ===== Étape 1: Extraction audio =====
            status_text.info(f"🎵 Étape 1/{total_steps} : Extraction de l'audio...")
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
            progress_bar.progress(20)
            
            # ===== Étape 2: Transcription =====
            if fast_mode:
                status_text.info(f"🎤 Étape 2/{total_steps} : Transcription API ({source_display})...")
                transcribe_cmd = [
                    python_exe, "transcribe_api.py", 
                    str(audio_file),
                    "-l", source_lang
                ]
            else:
                status_text.info(f"🎤 Étape 2/{total_steps} : Transcription locale ({source_display})...")
                transcribe_cmd = [
                    python_exe, "transcribe.py", 
                    str(audio_file),
                    "-l", source_lang,
                    "-m", model_size
                ]
            
            progress_bar.progress(25)
            
            result = subprocess.run(
                transcribe_cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                st.error(f"❌ Erreur lors de la transcription:\n{result.stderr}")
                st.stop()
            
            srt_file = video_path.with_suffix(".srt")
            progress_bar.progress(40)
            
            # ===== Étape 3: Traduction =====
            status_text.info(f"🌐 Étape 3/{total_steps} : Traduction → {target_display}...")
            progress_bar.progress(45)
            
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
            
            progress_bar.progress(60)
            
            # ===== Étape 4 (optionnel): Génération TTS =====
            dubbed_audio = None
            if enable_tts:
                status_text.info(f"🎙️ Étape 4/{total_steps} : Génération du doublage (Qwen3-TTS)...")
                progress_bar.progress(65)
                
                dubbed_audio = video_path.with_name(f"{video_path.stem}_{target_lang}_dubbed.wav")
                
                tts_cmd = [
                    python_exe, "generate.py",
                    str(srt_translated),
                    "-l", target_lang,
                    "-s", selected_speaker,
                    "-o", str(dubbed_audio),
                    "-d", "auto"
                ]
                
                # Ajouter l'audio de référence si fourni
                if use_voice_clone and ref_audio_file and ref_text:
                    # Sauvegarder l'audio de référence
                    ref_path = WORK_DIR / "ref_audio.wav"
                    with open(ref_path, "wb") as f:
                        f.write(ref_audio_file.getbuffer())
                    
                    tts_cmd.extend(["--ref-audio", str(ref_path), "--ref-text", ref_text])
                
                result = subprocess.run(
                    tts_cmd,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    st.warning(f"⚠️ Doublage échoué, continuation avec sous-titres uniquement:\n{result.stderr[:500]}")
                    dubbed_audio = None
                else:
                    st.success("🎙️ Doublage généré avec succès !")
                
                progress_bar.progress(80)
            
            # ===== Étape finale: Fusion vidéo =====
            status_text.info(f"🎬 Étape {total_steps}/{total_steps} : Fusion des sous-titres avec la vidéo...")
            progress_bar.progress(85)
            
            # Mapper le code langue vers le code ISO 639-2 pour FFmpeg
            lang_map = {
                "fr": "fre", "en": "eng", "es": "spa", "de": "ger",
                "it": "ita", "pt": "por", "zh": "chi", "ja": "jpn",
                "ko": "kor", "ru": "rus", "ar": "ara", "hi": "hin",
                "nl": "dut", "pl": "pol", "tr": "tur"
            }
            ffmpeg_lang = lang_map.get(target_lang, "und")
            
            if dubbed_audio and dubbed_audio.exists():
                # Fusion avec doublage (remplacer l'audio)
                output_video = video_path.with_name(f"{video_path.stem}_dubbed.mp4")
                ffmpeg_cmd = [
                    "ffmpeg", "-y",
                    "-i", str(video_path),
                    "-i", str(dubbed_audio),
                    "-i", str(srt_translated),
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-map", "2:0",
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k",
                    "-c:s", "mov_text",
                    "-metadata:s:s:0", f"language={ffmpeg_lang}",
                    "-metadata:s:s:0", f"title={TARGET_LANGUAGES[target_lang]['name']}",
                    "-metadata:s:a:0", f"language={ffmpeg_lang}",
                    str(output_video)
                ]
            else:
                # Fusion avec sous-titres uniquement
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
            
            # ===== Afficher les résultats =====
            if dubbed_audio and dubbed_audio.exists():
                st.success(f"🎉 Vidéo doublée créée : **{output_video.name}**")
            else:
                st.success(f"🎉 Vidéo sous-titrée créée : **{output_video.name}**")
            
            # Statistiques du cache
            new_stats = get_cache_stats()
            st.info(f"💾 {new_stats['total_entries']} traductions en cache")
            
            # Boutons de téléchargement
            col1, col2, col3 = st.columns(3)
            
            with col1:
                with open(output_video, "rb") as f:
                    st.download_button(
                        label="⬇️ Vidéo",
                        data=f,
                        file_name=output_video.name,
                        mime="video/mp4",
                        use_container_width=True
                    )
            
            with col2:
                with open(srt_translated, "r", encoding="utf-8") as f:
                    st.download_button(
                        label="⬇️ Sous-titres (.srt)",
                        data=f,
                        file_name=srt_translated.name,
                        mime="text/plain",
                        use_container_width=True
                    )
            
            with col3:
                if dubbed_audio and dubbed_audio.exists():
                    with open(dubbed_audio, "rb") as f:
                        st.download_button(
                            label="⬇️ Audio doublé (.wav)",
                            data=f,
                            file_name=dubbed_audio.name,
                            mime="audio/wav",
                            use_container_width=True
                        )
            
            # Aperçu du résultat
            st.subheader("📺 Aperçu du résultat")
            st.video(str(output_video))
            
            # Aperçu des sous-titres
            with st.expander("📝 Aperçu des sous-titres"):
                with open(srt_translated, "r", encoding="utf-8") as f:
                    preview = f.read(2000)
                    st.code(preview, language="")
            
        except Exception as e:
            st.error(f"❌ Une erreur inattendue s'est produite : {str(e)}")
            import traceback
            st.code(traceback.format_exc())

# Footer
st.divider()
col1, col2 = st.columns([3, 1])
with col1:
    st.caption("🎬 **Whisper Subtitle Generator** - Sous-titres & doublage automatiques avec IA")
with col2:
    st.caption("Qwen3-TTS • Whisper • Llama 3")
