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
            is_hardcode = False # Définir par défaut ici
    else:
        enable_tts = False
        selected_speaker = "fr-FR-DeniseNeural"
        keep_bg_music = False
        use_voice_clone = False
        ref_audio_file = None
        ref_text = None
        is_hardcode = False # Définir par défaut ici aussi
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

# ===== MAIN CONTENT =====
uploaded_file = st.file_uploader(
    "📁 Choisissez une vidéo (MP4, MKV, AVI)", 
    type=["mp4", "mkv", "avi"]
)

if uploaded_file is not None:
    # Sauvegarder le fichier uploadé
    video_path = file_service.save_uploaded_file(uploaded_file, uploaded_file.name)
    
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
            gender_emoji = "👩" if config.tts_speakers[selected_speaker]["gender"] == "female" else "👨"
            st.info(f"🎙️ Doublage: {gender_emoji} {selected_speaker}")
        else:
            st.info("📝 Sous-titres uniquement")
    
    # Afficher un aperçu de la vidéo
    with st.expander("👁️ Aperçu de la vidéo"):
        st.video(str(video_path))
    
    # Calculer le nombre d'étapes
    total_steps = 4
    if enable_tts:
        total_steps += 1
        if keep_bg_music:
            total_steps += 1
        if enable_diarization:
            total_steps += 1
    
    # Bouton de traitement
    if st.button("🚀 Lancer le traitement automatique", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        python_exe = sys.executable
        step = 1
        
        try:
            # ===== Étape 1: Extraction audio =====
            status_text.info(f"🎵 Étape {step}/{total_steps} : Extraction de l'audio...")
            progress_bar.progress(5)
            
            result = subprocess.run(
                [python_exe, "extract.py", str(video_path)],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                st.error(f"❌ Erreur lors de l'extraction audio:\n{result.stderr}")
                st.stop()
            
            audio_file = video_path.with_suffix(".wav")
            progress_bar.progress(10)
            step += 1
            
            # ===== Étape : Diarisation (Optionnel) =====
            diarization_data = None
            if enable_tts and enable_diarization:
                status_text.info(f"🕵️ Étape {step}/{total_steps} : Diarisation (Identification des personnages)...")
                
                result = subprocess.run(
                    [python_exe, "diarize.py", str(audio_file)],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    try:
                        import json
                        diarization_data = json.loads(result.stdout)
                        st.success("✅ Personnages identifiés !")
                    except Exception as e:
                        st.warning(f"⚠️ Erreur lecture diarisation: {e}")
                else:
                    st.warning(f"⚠️ Échec de la diarisation")
                
                progress_bar.progress(20)
                step += 1
            
            # ===== Étape 1.5: Séparation audio (Optionnel) =====
            bg_music_file = None
            if enable_tts and keep_bg_music:
                status_text.info(f"🎵 Étape {step}/{total_steps} : Séparation voix/musique (Demucs)...")
                
                result = subprocess.run(
                    [python_exe, "separate.py", str(audio_file)],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    bg_music_file = audio_file.parent / f"{audio_file.stem}_bg.wav"
                    st.success("✅ Musique de fond isolée !")
                else:
                    st.warning(f"⚠️ Échec de la séparation : {result.stderr}")
                
                progress_bar.progress(25)
                step += 1
            
            # ===== Étape 2: Transcription =====
            if fast_mode:
                status_text.info(f"🎤 Étape {step}/{total_steps} : Transcription API ({source_display})...")
                transcribe_cmd = [
                    python_exe, "transcribe_api.py", 
                    str(audio_file),
                    "-l", source_lang
                ]
            else:
                status_text.info(f"🎤 Étape {step}/{total_steps} : Transcription locale ({source_display})...")
                transcribe_cmd = [
                    python_exe, "transcribe.py", 
                    str(audio_file),
                    "-l", source_lang,
                    "-m", model_size
                ]
            
            progress_bar.progress(40)
            
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
            step += 1
            
            # ===== Étape 3: Traduction =====
            status_text.info(f"🌐 Étape {step}/{total_steps} : Traduction → {target_display}...")
            
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
            
            # Appliquer la diarisation au SRT traduit
            if diarization_data:
                with open(srt_translated, "r", encoding="utf-8") as f:
                    srt_content = f.read()
                
                # On ré-utilise une logique de parsing simple pour la cohérence
                blocks = re.split(r'\n\n+', srt_content.strip())
                new_blocks = []
                
                for block in blocks:
                    lines = block.split('\n')
                    if len(lines) >= 3:
                        time_match = re.search(r'(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})', lines[1])
                        if time_match:
                            # Utiliser une fonction de conversion simplifiée
                            def to_ms(t):
                                h, m, s, ms = map(int, re.split('[:.,]', t))
                                return (h * 3600 + m * 60 + s) * 1000 + ms
                            
                            start_ms = to_ms(time_match.group(1))
                            end_ms = to_ms(time_match.group(2))
                            mid_s = (start_ms + end_ms) / 2 / 1000
                            
                            # Trouver le speaker
                            spk_id = 0
                            for d_seg in diarization_data:
                                if d_seg['start'] <= mid_s <= d_seg['end']:
                                    spk_id = d_seg['speaker']
                                    break
                            
                            # Ajouter le tag au texte
                            lines[2] = f"[S{spk_id}] {lines[2]}"
                            new_blocks.append('\n'.join(lines))
                        else:
                            new_blocks.append(block)
                    else:
                        new_blocks.append(block)
                
                with open(srt_translated, "w", encoding="utf-8") as f:
                    f.write('\n\n'.join(new_blocks))

            progress_bar.progress(70)
            step += 1
            
            # ===== Étape 4 (optionnel): Génération TTS =====
            dubbed_audio = None
            if enable_tts:
                status_text.info(f"🎙️ Étape {step}/{total_steps} : Génération du doublage (Edge-TTS)...")
                dubbed_audio = video_path.with_name(f"{video_path.stem}_{target_lang}_dubbed.wav")
                
                # Liste des voix pour la langue cible
                lang_prefix = target_lang
                target_voices = [v for v in TTS_SPEAKERS.keys() if v.startswith(lang_prefix)]
                if not target_voices:
                    if target_lang == "zh": target_voices = [v for v in TTS_SPEAKERS.keys() if v.startswith("zh-CN")]
                    elif target_lang == "en": target_voices = [v for v in TTS_SPEAKERS.keys() if v.startswith("en-US")]
                if not target_voices: target_voices = ["fr-FR-DeniseNeural", "fr-FR-HenriNeural"]

                if enable_diarization:
                    voices_to_pass = [selected_speaker]
                    other_voices = [v for v in target_voices if v != selected_speaker]
                    voices_to_pass.extend(other_voices)
                    speakers_arg = ",".join(voices_to_pass)
                else:
                    speakers_arg = selected_speaker

                tts_cmd = [
                    python_exe, "generate.py",
                    str(srt_translated),
                    "-l", target_lang,
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
                
                progress_bar.progress(85)
                step += 1
            
            # ===== Étape finale: Fusion vidéo =====
            status_text.info(f"🎬 Étape {step}/{total_steps} : Fusion finale avec la vidéo...")
            progress_bar.progress(90)
            
            # Mapper le code langue vers le code ISO 639-2 pour FFmpeg
            lang_map = {
                "fr": "fre", "en": "eng", "es": "spa", "de": "ger",
                "it": "ita", "pt": "por", "zh": "chi", "ja": "jpn",
                "ko": "kor", "ru": "rus", "ar": "ara", "hi": "hin",
                "nl": "dut", "pl": "pol", "tr": "tur"
            }
            ffmpeg_lang = lang_map.get(target_lang, "und")
            
            if dubbed_audio and dubbed_audio.exists():
                # Fusion avec doublage
                output_video = video_path.with_name(f"{video_path.stem}_dubbed.mp4")
                
                # Préparation des filtres vidéo/audio
                v_codec = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22"] if is_hardcode else ["-c:v", "copy"]
                
                # Correction pour le filtre subtitles (gérer les espaces et les deux-points)
                if is_hardcode:
                    clean_srt_path = str(srt_translated).replace(":", "\\:").replace("'", "'\\''")
                    v_filter = ["-vf", f"subtitles='{clean_srt_path}'"]
                else:
                    v_filter = []
                
                if bg_music_file and bg_music_file.exists():
                    # Mixer doublage + musique de fond
                    ffmpeg_cmd = [
                        "ffmpeg", "-y",
                        "-i", str(video_path),
                        "-i", str(dubbed_audio),
                        "-i", str(bg_music_file),
                    ]
                    
                    if not is_hardcode:
                        ffmpeg_cmd.extend(["-i", str(srt_translated)])
                        
                    ffmpeg_cmd.extend([
                        "-filter_complex", "[1:a]volume=1.5[vov];[2:a]volume=0.8[bg];[vov][bg]amix=inputs=2:duration=longest[a]",
                        *v_filter,
                        "-map", "0:v:0",
                        "-map", "[a]",
                    ])
                    
                    if not is_hardcode:
                        ffmpeg_cmd.extend(["-map", "3:0"])
                    
                    ffmpeg_cmd.extend([
                        *v_codec,
                        "-c:a", "aac", "-b:a", "192k",
                    ])
                    
                    if not is_hardcode:
                        ffmpeg_cmd.extend([
                            "-c:s", "mov_text",
                            "-metadata:s:s:0", f"language={ffmpeg_lang}",
                            "-metadata:s:s:0", f"title={TARGET_LANGUAGES[target_lang]['name']}",
                        ])
                        
                    ffmpeg_cmd.extend([
                        "-metadata:s:a:0", f"language={ffmpeg_lang}",
                        str(output_video)
                    ])
                else:
                    # Doublage seul (remplacer l'audio original)
                    ffmpeg_cmd = [
                        "ffmpeg", "-y",
                        "-i", str(video_path),
                        "-i", str(dubbed_audio),
                    ]
                    
                    if not is_hardcode:
                        ffmpeg_cmd.extend(["-i", str(srt_translated)])
                        
                    ffmpeg_cmd.extend([*v_filter])
                    ffmpeg_cmd.extend(["-map", "0:v:0", "-map", "1:a:0"])
                    
                    if not is_hardcode:
                        ffmpeg_cmd.extend(["-map", "2:0"])
                        
                    ffmpeg_cmd.extend([
                        *v_codec,
                        "-c:a", "aac", "-b:a", "192k",
                    ])
                    
                    if not is_hardcode:
                        ffmpeg_cmd.extend([
                            "-c:s", "mov_text",
                            "-metadata:s:s:0", f"language={ffmpeg_lang}",
                            "-metadata:s:s:0", f"title={TARGET_LANGUAGES[target_lang]['name']}",
                        ])
                        
                    ffmpeg_cmd.extend([
                        "-metadata:s:a:0", f"language={ffmpeg_lang}",
                        str(output_video)
                    ])
            else:
                # Fusion avec sous-titres uniquement
                output_video = video_path.with_name(f"{video_path.stem}_vostfr.mp4")
                
                if is_hardcode:
                    clean_srt_path = str(srt_translated).replace(":", "\\:").replace("'", "'\\''")
                    ffmpeg_cmd = [
                        "ffmpeg", "-y",
                        "-i", str(video_path),
                        "-vf", f"subtitles='{clean_srt_path}'",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                        "-c:a", "copy",
                        str(output_video)
                    ]
                else:
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
