import os
import sys
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv  # <-- Importation nécessaire

# Charger les variables d'environnement du fichier .env
load_dotenv()

# Récupération de la clé API depuis l'environnement
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("❌ Erreur : La clé GROQ_API_KEY est introuvable dans le fichier .env")
    sys.exit(1)

# Configuration du client Groq
client = Groq(api_key=api_key)

def translate_text(text):
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Tu es un expert en traduction de sous-titres d'anime. Traduis le texte suivant en français. Réponds uniquement avec la traduction, sans guillemets ni explications."
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
        return content.strip() if content else text
    except Exception as e:
        print(f"Erreur lors de la traduction de '{text}': {e}")
        return text

if len(sys.argv) > 1:
    srt_input = Path(sys.argv[1])
else:
    print("Usage: python translate.py <srt_file>")
    sys.exit(1)

srt_output = srt_input.with_name(srt_input.stem + "_fr.srt")

print(f"Début de la traduction de {srt_input} vers {srt_output}...")

with open(srt_input, "r", encoding="utf-8") as f_in, open(srt_output, "w", encoding="utf-8") as f_out:
    block = []
    for line in f_in:
        line_strip = line.strip()
        if line_strip == "":
            if len(block) >= 3:
                num = block[0]
                times = block[1]
                text = " ".join(block[2:])
                
                # Traduction via API Groq
                text_fr = translate_text(text)
                
                f_out.write(f"{num}\n{times}\n{text_fr}\n\n")
            block = []
        else:
            block.append(line_strip)

    # Traiter le dernier bloc s'il existe
    if block and len(block) >= 3:
        num = block[0]
        times = block[1]
        text = " ".join(block[2:])
        text_fr = translate_text(text)
        f_out.write(f"{num}\n{times}\n{text_fr}\n\n")

print("Traduction terminée !")
