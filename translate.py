"""
Script de traduction de sous-titres avec cache et support multi-langues.
Utilise l'API Groq (Llama 3) pour la traduction.
"""

import os
import sys
import argparse
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv

# Import des modules locaux
from translation_cache import (
    get_cached_translation, 
    cache_translation, 
    get_cache_stats
)
from languages import (
    get_translation_prompt,
    WHISPER_LANGUAGES,
    TARGET_LANGUAGES
)
import srt_utils

# Charger les variables d'environnement du fichier .env
load_dotenv()

# Récupération de la clé API depuis l'environnement
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("❌ Erreur : La clé GROQ_API_KEY est introuvable dans le fichier .env")
    sys.exit(1)

# Configuration du client Groq
client = Groq(api_key=api_key)


def translate_text(text: str, source_lang: str = "ja", target_lang: str = "fr") -> str:
    """
    Traduit un texte avec cache.
    
    Args:
        text: Texte à traduire
        source_lang: Code de la langue source (défaut: "ja")
        target_lang: Code de la langue cible (défaut: "fr")
    
    Returns:
        Le texte traduit
    """
    # Vérifier le cache en premier
    cached = get_cached_translation(text, source_lang, target_lang)
    if cached:
        return cached.get("translation", cached) if isinstance(cached, dict) else cached
    
    try:
        # Obtenir le prompt adapté
        system_prompt = get_translation_prompt(source_lang, target_lang)
        
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": text,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
        )
        content = chat_completion.choices[0].message.content
        translation = content.strip() if content else text
        
        # Mettre en cache la traduction
        cache_translation(text, translation, source_lang, target_lang)
        
        return translation
        
    except Exception as e:
        print(f"⚠️ Erreur lors de la traduction de '{text[:50]}...': {e}")
        return text


def translate_srt(
    srt_input: Path, 
    srt_output: Path, 
    source_lang: str = "ja", 
    target_lang: str = "fr"
) -> tuple:
    """
    Traduit un fichier SRT complet.
    
    Args:
        srt_input: Chemin du fichier SRT source
        srt_output: Chemin du fichier SRT de sortie
        source_lang: Code de la langue source
        target_lang: Code de la langue cible
    
    Returns:
        Tuple (nombre de lignes traduites, nombre de lignes depuis le cache)
    """
    translated_count = 0
    cached_count = 0
    
    print(f"🌐 Traduction {source_lang} → {target_lang}")
    print(f"📄 Source: {srt_input}")
    print(f"📄 Sortie: {srt_output}")
    
    with open(srt_output, "w", encoding="utf-8") as f_out:
        for block in srt_utils.read_srt_blocks(srt_input):
            num = block[0]
            times = block[1]
            text = " ".join(block[2:])
            
            # Vérifier si c'est une traduction depuis le cache
            cached = get_cached_translation(text, source_lang, target_lang)

            # Traduction via API Groq (avec cache intégré)
            text_translated = translate_text(text, source_lang, target_lang)
            
            if cached:
                cached_count += 1
                print(f"  💾 [{num}] (cache)")
            else:
                translated_count += 1
                print(f"  ✅ [{num}] Traduit")

            f_out.write(f"{num}\n{times}\n{text_translated}\n\n")
    
    return translated_count, cached_count


def main():
    parser = argparse.ArgumentParser(
        description="Traducteur de sous-titres SRT avec cache"
    )
    parser.add_argument("srt_file", type=str, help="Fichier SRT à traduire")
    parser.add_argument(
        "-s", "--source", 
        type=str, 
        default="ja",
        choices=list(WHISPER_LANGUAGES.keys()),
        help="Langue source (défaut: ja)"
    )
    parser.add_argument(
        "-t", "--target", 
        type=str, 
        default="fr",
        choices=list(TARGET_LANGUAGES.keys()),
        help="Langue cible (défaut: fr)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Fichier de sortie (défaut: {nom}_fr.srt)"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Afficher les statistiques du cache"
    )
    
    args = parser.parse_args()
    
    # Afficher les stats du cache si demandé
    if args.stats:
        stats = get_cache_stats()
        print(f"📊 Statistiques du cache:")
        print(f"   • Entrées totales: {stats['total_entries']}")
        print(f"   • Paires de langues: {', '.join(stats['languages']) or 'Aucune'}")
        return
    
    srt_input = Path(args.srt_file)
    
    if not srt_input.exists():
        print(f"❌ Fichier introuvable: {srt_input}")
        sys.exit(1)
    
    # Définir le fichier de sortie
    if args.output:
        srt_output = Path(args.output)
    else:
        srt_output = srt_input.with_name(f"{srt_input.stem}_{args.target}.srt")
    
    print(f"\n{'='*50}")
    print(f"🎬 Traducteur de sous-titres")
    print(f"{'='*50}")
    
    # Stats du cache avant traduction
    stats_before = get_cache_stats()
    print(f"💾 Cache: {stats_before['total_entries']} traductions en mémoire")
    
    # Traduction
    translated, cached = translate_srt(
        srt_input, 
        srt_output, 
        args.source, 
        args.target
    )
    
    print(f"\n{'='*50}")
    print(f"✅ Traduction terminée !")
    print(f"   • Nouvelles traductions: {translated}")
    print(f"   • Depuis le cache: {cached}")
    print(f"   • Fichier: {srt_output}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
