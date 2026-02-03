---
title: Whisper Subtitle Generator
emoji: 🎬
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# 🎬 Whisper Subtitle Generator

Générateur automatique de sous-titres multilingues et doublage IA pour vidéos.

## ✨ Fonctionnalités

- **🌍 Multi-langues** : 15 langues sources (japonais, coréen, chinois, anglais...) et 15 langues cibles
- **💾 Cache intelligent** : Les traductions sont mises en cache pour éviter les appels API redondants
- **⚡ Mode rapide** : API Groq Whisper pour une transcription ultra-rapide
- **🎯 Auto-détection** : Détection automatique de la langue source
- **🎙️ Doublage IA** : Génération audio avec Qwen3-TTS (clonage vocal supporté)
- **🖥️ Interface web** : Application Streamlit intuitive
- **📦 CLI complet** : Pipeline en ligne de commande avec arguments

## 🚀 Déploiement sur Streamlit Cloud

### Prérequis

1. Un compte [Streamlit Cloud](https://streamlit.io/cloud)
2. Une clé API [Groq](https://console.groq.com/)

### Configuration des secrets

Dans Streamlit Cloud, allez dans **Settings > Secrets** et ajoutez :

```toml
GROQ_API_KEY = "votre_clé_groq_ici"
```

### Déploiement

1. Forkez ou clonez ce repository
2. Connectez-vous à Streamlit Cloud
3. Créez une nouvelle app en pointant vers ce repository
4. Configurez le secret `GROQ_API_KEY`
5. Déployez !

## 🛠️ Installation locale

```bash
# Cloner le repository
git clone https://github.com/octavebahoun/Whisper-subtitle.git
cd Whisper-subtitle

# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Optionnel: Flash Attention pour GPU (accélération TTS)
pip install flash-attn --no-build-isolation

# Créer un fichier .env
echo "GROQ_API_KEY=votre_clé_ici" > .env

# Lancer l'application
streamlit run app.py
```

## 📖 Utilisation

### Interface Web (Streamlit)

```bash
streamlit run app.py
```

Puis :

1. Sélectionnez la langue source et cible dans la sidebar
2. Uploadez votre vidéo
3. Cliquez sur "Lancer le traitement"
4. Téléchargez la vidéo sous-titrée !

### Ligne de commande (Pipeline)

```bash
# Japonais → Français (défaut)
python pipeline.py video.mp4

# Coréen → Anglais
python pipeline.py video.mp4 -s ko -t en

# Chinois → Français avec Whisper local
python pipeline.py video.mp4 -s zh -t fr --local -m medium

# Avec doublage IA
python pipeline.py video.mp4 -s ja -t fr --dub

# Doublage avec clonage vocal
python pipeline.py video.mp4 --dub --ref-audio voice.wav --ref-text "Texte prononcé"

# Voir toutes les options
python pipeline.py --help
```

### Scripts individuels

```bash
# Extraction audio
python extract.py video.mp4

# Transcription API (rapide)
python transcribe_api.py audio.wav -l ja

# Transcription locale
python transcribe.py audio.wav -l ko -m small

# Traduction avec cache
python translate.py subtitles.srt -s ja -t fr

# Génération doublage
python generate.py subtitles_fr.srt -l fr

# Doublage avec clonage vocal
python generate.py subtitles_fr.srt -l fr --ref-audio voice.wav --ref-text "Exemple"

# Statistiques du cache
python translate.py --stats
```

## 🎙️ Doublage IA (TTS)

Le projet intègre **Qwen3-TTS 0.6B** pour générer des doublages automatiques.

### Caractéristiques

- **10 langues supportées** : Français, Anglais, Japonais, Chinois, Coréen, Allemand, Espagnol, Italien, Portugais, Russe
- **~2GB VRAM** : Fonctionne sur GPU modeste
- **Clonage vocal** : Peut imiter une voix de référence en 3 secondes
- **Synchronisation** : Audio synchronisé avec les timestamps des sous-titres

### Exemple d'utilisation

```bash
# Doublage simple
python generate.py video_fr.srt -l fr

# Avec clonage vocal
python generate.py video_fr.srt -l fr \
    --ref-audio sample_voice.wav \
    --ref-text "Bonjour, comment allez-vous ?"
```

### Langues TTS

| Code | Langue    |
| ---- | --------- |
| `fr` | Français  |
| `en` | English   |
| `ja` | 日本語    |
| `zh` | 中文      |
| `ko` | 한국어    |
| `de` | Deutsch   |
| `es` | Español   |
| `it` | Italiano  |
| `pt` | Português |
| `ru` | Русский   |

## 🌍 Langues de transcription

### Sources (transcription) - 15 langues

| Code   | Langue            |     | Code | Langue        |
| ------ | ----------------- | --- | ---- | ------------- |
| `ja`   | 🇯🇵 Japonais       |     | `ko` | 🇰🇷 Coréen     |
| `zh`   | 🇨🇳 Chinois        |     | `en` | 🇬🇧 Anglais    |
| `es`   | 🇪🇸 Espagnol       |     | `de` | 🇩🇪 Allemand   |
| `it`   | 🇮🇹 Italien        |     | `pt` | 🇵🇹 Portugais  |
| `ru`   | 🇷🇺 Russe          |     | `ar` | 🇸🇦 Arabe      |
| `hi`   | 🇮🇳 Hindi          |     | `th` | 🇹🇭 Thaï       |
| `vi`   | 🇻🇳 Vietnamien     |     | `id` | 🇮🇩 Indonésien |
| `auto` | 🔍 Auto-détection |     |      |               |

### Cibles (traduction) - 15 langues

| Code | Langue         |     | Code | Langue       |
| ---- | -------------- | --- | ---- | ------------ |
| `fr` | 🇫🇷 Français    |     | `en` | 🇬🇧 Anglais   |
| `es` | 🇪🇸 Espagnol    |     | `de` | 🇩🇪 Allemand  |
| `it` | 🇮🇹 Italien     |     | `pt` | 🇵🇹 Portugais |
| `zh` | 🇨🇳 Chinois     |     | `ja` | 🇯🇵 Japonais  |
| `ko` | 🇰🇷 Coréen      |     | `ru` | 🇷🇺 Russe     |
| `ar` | 🇸🇦 Arabe       |     | `hi` | 🇮🇳 Hindi     |
| `nl` | 🇳🇱 Néerlandais |     | `pl` | 🇵🇱 Polonais  |
| `tr` | 🇹🇷 Turc        |     |      |              |

## 💾 Cache de traduction

Le système de cache stocke automatiquement toutes les traductions effectuées.

**Avantages :**

- ⚡ Évite les appels API redondants
- 💰 Réduit les coûts d'API
- 🔄 Accélère le retraitement de fichiers similaires

**Gestion du cache :**

```bash
# Voir les statistiques
python translate.py --stats

# Le cache est stocké dans translations_cache.json
```

## 📋 Technologies

| Technologie   | Usage                                       |
| ------------- | ------------------------------------------- |
| **Streamlit** | Interface web                               |
| **Whisper**   | Transcription audio → texte                 |
| **Groq API**  | Transcription rapide + Traduction (Llama 3) |
| **Qwen3-TTS** | Synthèse vocale / Doublage                  |
| **FFmpeg**    | Traitement vidéo/audio                      |

## 📁 Structure du projet

```
├── app.py                  # Interface Streamlit
├── pipeline.py             # Pipeline CLI complet
├── extract.py              # Extraction audio
├── transcribe.py           # Transcription Whisper locale
├── transcribe_api.py       # Transcription API Groq
├── translate.py            # Traduction avec cache
├── generate.py             # Génération doublage TTS
├── languages.py            # Configuration des langues
├── translation_cache.py    # Module de cache
├── requirements.txt        # Dépendances Python
├── packages.txt            # Dépendances système
└── .streamlit/             # Configuration Streamlit
```

## ⚙️ Configuration GPU

Pour de meilleures performances TTS :

```bash
# Installer Flash Attention 2 (nécessite CUDA)
pip install flash-attn --no-build-isolation

# Le script détecte automatiquement le GPU disponible
python generate.py subtitles.srt -d cuda:0
```

## 📝 Licence

MIT
