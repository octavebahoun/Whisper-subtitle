"""
Script de génération audio (doublage) à partir de sous-titres.
Utilise Qwen3-TTS 0.6B pour synthétiser la voix.

Prérequis:
    pip install -U qwen-tts soundfile numpy tqdm
    # Optionnel pour performance GPU:
    pip install -U flash-attn --no-build-isolation
"""

import sys
import argparse
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

try:
    import torch
    import soundfile as sf
    import numpy as np
    from tqdm import tqdm
except ImportError as e:
    print(f"❌ Dépendance manquante: {e}")
    print("💡 Installez: pip install torch soundfile numpy tqdm")
    sys.exit(1)

# Langues supportées par Qwen3-TTS
TTS_LANGUAGES = {
    "fr": "French",
    "en": "English", 
    "ja": "Japanese",
    "zh": "Chinese",
    "ko": "Korean",
    "de": "German",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
}


@dataclass
class SubtitleSegment:
    """Représente un segment de sous-titre."""
    index: int
    start: float
    end: float
    text: str


def parse_srt_time(time_str: str) -> float:
    """Convertit un timestamp SRT en secondes."""
    # Format: HH:MM:SS,mmm
    match = re.match(r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})', time_str)
    if match:
        h, m, s, ms = map(int, match.groups())
        return h * 3600 + m * 60 + s + ms / 1000
    return 0.0


def parse_srt(srt_path: Path) -> list[SubtitleSegment]:
    """Parse un fichier SRT et retourne une liste de segments."""
    segments = []
    
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Séparer les blocs par double retour à la ligne
    blocks = re.split(r'\n\n+', content.strip())
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            try:
                index = int(lines[0])
                
                # Parser les timestamps
                time_match = re.match(
                    r'(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})',
                    lines[1]
                )
                if time_match:
                    start = parse_srt_time(time_match.group(1))
                    end = parse_srt_time(time_match.group(2))
                    text = ' '.join(lines[2:]).strip()
                    
                    if text:  # Ignorer les segments vides
                        segments.append(SubtitleSegment(
                            index=index,
                            start=start,
                            end=end,
                            text=text
                        ))
            except ValueError:
                continue
    
    return segments


def load_tts_model(device: str = "auto", use_flash_attn: bool = True):
    """
    Charge le modèle Qwen3-TTS.
    
    Args:
        device: "cuda", "cpu", ou "auto"
        use_flash_attn: Utiliser Flash Attention 2 (plus rapide sur GPU)
    """
    try:
        from qwen_tts import Qwen3TTSModel
    except ImportError:
        print("❌ qwen-tts n'est pas installé")
        print("💡 Installez: pip install -U qwen-tts")
        sys.exit(1)
    
    # Déterminer le device
    if device == "auto":
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
    
    print(f"🔧 Chargement du modèle Qwen3-TTS-0.6B sur {device}...")
    
    # Configuration du modèle
    model_kwargs = {
        "device_map": device,
    }
    
    if device.startswith("cuda"):
        model_kwargs["dtype"] = torch.bfloat16
        if use_flash_attn:
            try:
                model_kwargs["attn_implementation"] = "flash_attention_2"
                print("   ⚡ Flash Attention 2 activé")
            except Exception:
                print("   ⚠️ Flash Attention non disponible, utilisation standard")
    else:
        model_kwargs["dtype"] = torch.float32
        print("   ⚠️ CPU détecté - la génération sera plus lente")
    
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        **model_kwargs
    )
    
    print("   ✅ Modèle chargé")
    return model


def generate_segment_audio(
    model, 
    text: str, 
    language: str,
    ref_audio: Optional[str] = None,
    ref_text: Optional[str] = None
) -> tuple:
    """
    Génère l'audio pour un segment de texte.
    
    Args:
        model: Modèle Qwen3-TTS
        text: Texte à synthétiser
        language: Langue (en anglais, ex: "French")
        ref_audio: Audio de référence pour le clonage vocal (optionnel)
        ref_text: Texte de l'audio de référence (optionnel)
    
    Returns:
        Tuple (audio_array, sample_rate)
    """
    if ref_audio and ref_text:
        # Mode clonage vocal
        wavs, sr = model.generate_voice_clone(
            text=text,
            language=language,
            ref_audio=ref_audio,
            ref_text=ref_text,
        )
    else:
        # Mode synthèse standard
        wavs, sr = model.generate(
            text=text,
            language=language,
        )
    
    return wavs[0], sr


def generate_dubbed_audio(
    srt_path: Path,
    output_path: Path,
    language: str = "fr",
    ref_audio: Optional[str] = None,
    ref_text: Optional[str] = None,
    device: str = "auto"
) -> Path:
    """
    Génère un fichier audio doublé à partir des sous-titres.
    
    Args:
        srt_path: Chemin vers le fichier SRT
        output_path: Chemin de sortie pour l'audio
        language: Code langue (fr, en, ja, etc.)
        ref_audio: Audio de référence pour clonage vocal
        ref_text: Texte de l'audio de référence
        device: Device pour le modèle
    
    Returns:
        Chemin vers le fichier audio généré
    """
    # Vérifier la langue
    lang_name = TTS_LANGUAGES.get(language)
    if not lang_name:
        print(f"❌ Langue '{language}' non supportée par TTS")
        print(f"💡 Langues disponibles: {', '.join(TTS_LANGUAGES.keys())}")
        sys.exit(1)
    
    print(f"🎙️ Génération de doublage")
    print(f"📄 Sous-titres: {srt_path}")
    print(f"🌍 Langue: {lang_name}")
    print(f"📁 Sortie: {output_path}")
    
    # Parser les sous-titres
    segments = parse_srt(srt_path)
    if not segments:
        print("❌ Aucun segment trouvé dans le fichier SRT")
        sys.exit(1)
    
    print(f"📝 {len(segments)} segments à générer")
    
    # Charger le modèle
    model = load_tts_model(device)
    
    # Déterminer la durée totale (dernier segment + marge)
    total_duration = max(seg.end for seg in segments) + 1.0
    sample_rate = 24000  # Sera mis à jour par le modèle
    
    # Générer audio pour chaque segment
    audio_segments = []
    
    for seg in tqdm(segments, desc="🔊 Génération"):
        try:
            audio, sr = generate_segment_audio(
                model=model,
                text=seg.text,
                language=lang_name,
                ref_audio=ref_audio,
                ref_text=ref_text
            )
            sample_rate = sr
            audio_segments.append({
                'start': seg.start,
                'end': seg.end,
                'audio': audio,
                'text': seg.text
            })
        except Exception as e:
            print(f"\n⚠️ Erreur segment {seg.index}: {e}")
            # Créer un segment silencieux
            silence_duration = seg.end - seg.start
            silence = np.zeros(int(silence_duration * sample_rate))
            audio_segments.append({
                'start': seg.start,
                'end': seg.end,
                'audio': silence,
                'text': seg.text
            })
    
    # Assembler l'audio final avec timing correct
    print("\n🔧 Assemblage de l'audio final...")
    
    # Créer un buffer pour toute la durée
    total_samples = int(total_duration * sample_rate)
    final_audio = np.zeros(total_samples)
    
    for seg_data in audio_segments:
        start_sample = int(seg_data['start'] * sample_rate)
        audio = seg_data['audio']
        
        # Calculer la durée disponible
        available_duration = seg_data['end'] - seg_data['start']
        available_samples = int(available_duration * sample_rate)
        
        # Ajuster la longueur de l'audio si nécessaire
        if len(audio) > available_samples:
            # L'audio est trop long, on le coupe
            audio = audio[:available_samples]
        elif len(audio) < available_samples:
            # L'audio est trop court, on ajoute du silence
            padding = np.zeros(available_samples - len(audio))
            audio = np.concatenate([audio, padding])
        
        # Insérer dans le buffer final
        end_sample = start_sample + len(audio)
        if end_sample <= total_samples:
            # Mixer avec l'existant (au cas où il y a overlap)
            final_audio[start_sample:end_sample] += audio
    
    # Normaliser pour éviter le clipping
    max_val = np.max(np.abs(final_audio))
    if max_val > 0:
        final_audio = final_audio / max_val * 0.9
    
    # Sauvegarder
    sf.write(str(output_path), final_audio, sample_rate)
    
    print(f"✅ Audio doublé généré: {output_path}")
    print(f"   ⏱️ Durée: {total_duration:.1f}s")
    print(f"   🎵 Sample rate: {sample_rate}Hz")
    
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Génère un doublage audio à partir de sous-titres avec Qwen3-TTS"
    )
    parser.add_argument(
        "srt_file", 
        type=str, 
        help="Fichier SRT contenant les sous-titres traduits"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Fichier audio de sortie (défaut: {nom}_dubbed.wav)"
    )
    parser.add_argument(
        "-l", "--language",
        type=str,
        default="fr",
        choices=list(TTS_LANGUAGES.keys()),
        help="Langue des sous-titres (défaut: fr)"
    )
    parser.add_argument(
        "--ref-audio",
        type=str,
        default=None,
        help="Audio de référence pour le clonage vocal"
    )
    parser.add_argument(
        "--ref-text",
        type=str,
        default=None,
        help="Texte prononcé dans l'audio de référence"
    )
    parser.add_argument(
        "-d", "--device",
        type=str,
        default="auto",
        choices=["auto", "cuda:0", "cuda:1", "cpu"],
        help="Device pour le modèle (défaut: auto)"
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="Afficher les langues supportées"
    )
    
    args = parser.parse_args()
    
    if args.list_voices:
        print("🌍 Langues supportées par Qwen3-TTS:")
        for code, name in TTS_LANGUAGES.items():
            print(f"   {code}: {name}")
        return
    
    srt_path = Path(args.srt_file)
    
    if not srt_path.exists():
        print(f"❌ Fichier introuvable: {srt_path}")
        sys.exit(1)
    
    # Définir le fichier de sortie
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = srt_path.with_name(f"{srt_path.stem}_dubbed.wav")
    
    # Vérifier les paramètres de clonage vocal
    if (args.ref_audio and not args.ref_text) or (args.ref_text and not args.ref_audio):
        print("❌ Pour le clonage vocal, --ref-audio et --ref-text sont tous deux requis")
        sys.exit(1)
    
    generate_dubbed_audio(
        srt_path=srt_path,
        output_path=output_path,
        language=args.language,
        ref_audio=args.ref_audio,
        ref_text=args.ref_text,
        device=args.device
    )


if __name__ == "__main__":
    main()
