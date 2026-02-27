"""
Refactored Application Streamlit - Générateur automatique de sous-titres et doublage.
Supporte plusieurs langues sources et cibles avec cache de traduction.
"""

import streamlit as st
import subprocess
import sys
from pathlib import Path
import os
import json

# Import des modules refacturés
from config import config
from services.api_service import APIService
from services.file_service import FileService
from services.subtitle_service import SubtitleService
from services.tts_service import TTSService
from services.ffmpeg_service import FFmpegService
from utils.progress_tracker import ProgressTracker
from languages import (
    WHISPER_LANGUAGES, 
    TARGET_LANGUAGES,
    get_language_display
)
from translation_cache import get_cache_stats, clear_cache

def main():
    # Initialisation des services
    api_service = APIService()
    file_service = FileService(config.work_dir)
    subtitle_service = SubtitleService()
    tts_service = TTSService(config.tts_speakers)
    ffmpeg_service = FFmpegService()

    # Créer un fichier .env temporaire pour les scripts esclaves
    api_service.create_env_file()

    # Configuration de l'application
    st.set_page_config(page_title="Auto VOSTFR + Doublage", page_icon="🎬", layout="wide")
    st.title("🎬 Générateur de sous-titres & doublage IA")
    st.markdown("**Uploadez une vidéo et obtenez automatiquement des sous-titres traduits et/ou un doublage IA**")

    # Sidebar pour les paramètres
    params = setup_sidebar(tts_service)

    # Main content
    uploaded_file = st.file_uploader(
        "📁 Choisissez une vidéo (MP4, MKV, AVI)", 
        type=["mp4", "mkv", "avi"]
    )

    if uploaded_file is not None:
        process_video(
            uploaded_file, 
            params, 
            file_service, 
            subtitle_service, 
            tts_service, 
            ffmpeg_service,
            api_service
        )


def setup_sidebar(tts_service):
    """
    Setup the sidebar with all the parameters
    """
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
        tts_available = target_lang in config.tts_languages
        
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
                female_voices = tts_service.get_voices_by_gender("female")
                male_voices = tts_service.get_voices_by_gender("male")
                
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
                    name: tts_service.get_voice_label(name)
                    for name in available_speakers
                }
                
                selected_speaker = st.selectbox(
                    "Voix",
                    options=list(speaker_options.keys()),
                    format_func=lambda x: speaker_options[x],
                    index=list(speaker_options.keys()).index(default_speaker) if default_speaker in speaker_options else 0,
                    help="Choisissez la voix pour le doublage"
                )

                keep_bg_music = st.toggle(
                    "Garder la musique de fond",
                    value=True,
                    help="Sépare la musique de la voix originale pour la garder dans le doublage"
                )
                
                # Option clonage vocal
                use_voice_clone = st.toggle(
                    "Clonage vocal (expérimental)",
                    value=False,
                    help="Utiliser un audio de référence pour cloner une voix"
                )

                # Option Multi-Speaker Diarisation
                enable_diarization = st.toggle(
                    "Multi-locuteurs (Diarisation)",
                    value=False,
                    help="Détecte automatiquement les différents personnages et leur attribue des voix différentes"
                )
                
                # --- Nouvelle option : Type d'export ---
                st.divider()
                st.subheader("🎬 Export Vidéo")
                subtitle_type = st.radio(
                    "Incrustation des sous-titres",
                    options=["Activables (Softcode)", "Fixes (Hardcode)"],
                    index=0,
                    help="Softcode : On peut les désactiver. Hardcode : Ils font partie de l'image (meilleure compatibilité)."
                )
                is_hardcode = subtitle_type == "Fixes (Hardcode)"
                
                if enable_diarization:
                    st.info("🎭 Diarisation activée : les différents personnages auront des voix différentes")
                    num_speakers = st.number_input("Nombre de personnages (approximatif)", min_value=1, max_value=5, value=2)
                else:
                    num_speakers = 1
                
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
                selected_speaker = "fr-FR-DeniseNeural"
                keep_bg_music = False
                use_voice_clone = False
                ref_audio_file = None
                ref_text = None
                is_hardcode = False  # Définir par défaut ici
        else:
            enable_tts = False
            selected_speaker = "fr-FR-DeniseNeural"
            keep_bg_music = False
            use_voice_clone = False
            ref_audio_file = None
            ref_text = None
            is_hardcode = False  # Définir par défaut ici aussi
            st.warning(f"⚠️ TTS non disponible pour {TARGET_LANGUAGES[target_lang]['name']}")
            st.caption(f"Langues TTS: {', '.join(config.tts_languages)}")
        
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
                    file_service.clean_work_directory()
                    st.success("Nettoyé !")
                except Exception as e:
                    st.error(f"Erreur: {e}")

    # Retourner les paramètres configurés
    return {
        'source_lang': source_lang,
        'target_lang': target_lang,
        'fast_mode': fast_mode,
        'model_size': model_size,
        'enable_tts': enable_tts,
        'selected_speaker': selected_speaker,
        'keep_bg_music': keep_bg_music,
        'use_voice_clone': use_voice_clone,
        'ref_audio_file': ref_audio_file,
        'ref_text': ref_text,
        'is_hardcode': is_hardcode,
        'enable_diarization': enable_diarization,
        'num_speakers': num_speakers
    }


def process_video(uploaded_file, params, file_service, subtitle_service, tts_service, ffmpeg_service, api_service):
    """
    Process the uploaded video with the specified parameters
    """
    # Sauvegarder le fichier uploadé
    video_path = file_service.save_uploaded_file(uploaded_file, uploaded_file.name)
    
    source_display = f"{WHISPER_LANGUAGES[params['source_lang']]['emoji']} {WHISPER_LANGUAGES[params['source_lang']]['name']}"
    target_display = f"{TARGET_LANGUAGES[params['target_lang']]['emoji']} {TARGET_LANGUAGES[params['target_lang']]['name']}"
    
    st.success(f"✅ Vidéo chargée : **{uploaded_file.name}**")
    
    # Afficher les paramètres sélectionnés
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"🌐 {source_display} → {target_display}")
    with col2:
        st.info(f"⚡ {'API Groq' if params['fast_mode'] else f'Whisper {params['model_size']}'}")
    with col3:
        if params['enable_tts']:
            gender_emoji = "👩" if config.tts_speakers[params['selected_speaker']]["gender"] == "female" else "👨"
            st.info(f"🎙️ Doublage: {gender_emoji} {params['selected_speaker']}")
        else:
            st.info("📝 Sous-titres uniquement")
    
    # Afficher un aperçu de la vidéo
    with st.expander("👁️ Aperçu de la vidéo"):
        st.video(str(video_path))
    
    # Calculer le nombre d'étapes
    total_steps = 4
    if params['enable_tts']:
        total_steps += 1
        if params['keep_bg_music']:
            total_steps += 1
        if params['enable_diarization']:
            total_steps += 1
    
    # Bouton de traitement
    if st.button("🚀 Lancer le traitement automatique", type="primary", use_container_width=True):
        progress_tracker = ProgressTracker(total_steps)
        python_exe = sys.executable
        
        try:
            # Obtenir les chemins de sortie standard
            output_paths = file_service.get_output_paths(video_path, params['target_lang'])
            
            step = 1
            
            # ===== Étape 1: Extraction audio =====
            progress_tracker.update(step, f"🎵 Étape {step}/{total_steps} : Extraction de l'audio...")
            
            result = subprocess.run(
                [python_exe, "extract.py", str(video_path)],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                st.error(f"❌ Erreur lors de l'extraction audio:\n{result.stderr}")
                st.stop()
            
            audio_file = output_paths["audio"]
            step += 1
            
            # ===== Étape : Diarisation (Optionnel) =====
            diarization_data = None
            if params['enable_tts'] and params['enable_diarization']:
                progress_tracker.update(step, f"🕵️ Étape {step}/{total_steps} : Diarisation (Identification des personnages)...")
                
                result = subprocess.run(
                    [python_exe, "diarize.py", str(audio_file)],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    try:
                        diarization_data = json.loads(result.stdout)
                        st.success("✅ Personnages identifiés !")
                    except Exception as e:
                        st.warning(f"⚠️ Erreur lecture diarisation: {e}")
                else:
                    st.warning(f"⚠️ Échec de la diarisation")
                
                step += 1
            
            # ===== Étape : Séparation audio (Optionnel) =====
            bg_music_file = None
            if params['enable_tts'] and params['keep_bg_music']:
                progress_tracker.update(step, f"🎵 Étape {step}/{total_steps} : Séparation voix/musique (Demucs)...")
                
                result = subprocess.run(
                    [python_exe, "separate.py", str(audio_file)],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    bg_music_file = output_paths["bg_music"]
                    st.success("✅ Musique de fond isolée !")
                else:
                    st.warning(f"⚠️ Échec de la séparation : {result.stderr}")
                
                step += 1
            
            # ===== Étape 2: Transcription =====
            if params['fast_mode']:
                progress_tracker.update(step, f"🎤 Étape {step}/{total_steps} : Transcription API ({source_display})...")
                transcribe_cmd = [
                    python_exe, "transcribe_api.py", 
                    str(audio_file),
                    "-l", params['source_lang']
                ]
            else:
                progress_tracker.update(step, f"🎤 Étape {step}/{total_steps} : Transcription locale ({source_display})...")
                transcribe_cmd = [
                    python_exe, "transcribe.py", 
                    str(audio_file),
                    "-l", params['source_lang'],
                    "-m", params['model_size']
                ]
            
            result = subprocess.run(
                transcribe_cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                st.error(f"❌ Erreur lors de la transcription:\n{result.stderr}")
                st.stop()
            
            srt_file = output_paths["srt_original"]
            step += 1
            
            # ===== Étape 3: Traduction =====
            progress_tracker.update(step, f"🌐 Étape {step}/{total_steps} : Traduction → {target_display}...")
            
            srt_translated = output_paths["srt_translated"]
            
            result = subprocess.run(
                [
                    python_exe, "translate.py", 
                    str(srt_file),
                    "-s", params['source_lang'],
                    "-t", params['target_lang'],
                    "-o", str(srt_translated)
                ],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                st.error(f"❌ Erreur lors de la traduction:\n{result.stderr}")
                st.stop()
            
            # Appliquer la diarisation au SRT traduit
            if diarization_data:
                subtitle_service.apply_diarization_to_srt(srt_translated, diarization_data, srt_translated)

            step += 1
            
            # ===== Étape 4 (optionnel): Génération TTS =====
            dubbed_audio = None
            if params['enable_tts']:
                progress_tracker.update(step, f"🎙️ Étape {step}/{total_steps} : Génération du doublage (Edge-TTS)...")
                dubbed_audio = output_paths["dubbed_audio"]
                
                # Liste des voix pour la langue cible
                target_voices = tts_service.get_target_voices(params['target_lang'])

                speakers_arg = tts_service.build_speakers_argument(
                    params['selected_speaker'], 
                    target_voices, 
                    params['enable_diarization']
                )

                tts_cmd = [
                    python_exe, "generate.py",
                    str(srt_translated),
                    "-l", params['target_lang'],
                    "-s", speakers_arg,
                    "-o", str(dubbed_audio)
                ]
                
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
                
                step += 1
            
            # ===== Étape finale: Fusion vidéo =====
            progress_tracker.update(step, f"🎬 Étape {step}/{total_steps} : Fusion finale avec la vidéo...")
            
            # Déterminer le chemin de sortie
            if dubbed_audio and dubbed_audio.exists():
                output_video = output_paths["output_video"]
            else:
                output_video = output_paths["subtitle_video"]
            
            # Construire la commande FFmpeg
            cmd = ffmpeg_service.build_ffmpeg_command(
                video_path=video_path,
                output_path=output_video,
                srt_path=srt_translated,
                dubbed_audio_path=dubbed_audio,
                bg_music_path=bg_music_file,
                target_lang=params['target_lang'],
                is_hardcode=params['is_hardcode']
            )
            
            # Exécuter la commande FFmpeg
            success = ffmpeg_service.execute_ffmpeg_command(cmd)
            
            if not success:
                st.error(f"❌ Erreur lors de la fusion FFmpeg")
                st.stop()
            
            progress_tracker.complete()
            
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


if __name__ == "__main__":
    main()