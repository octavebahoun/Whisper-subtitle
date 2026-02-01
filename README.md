# Whisper Subtitle Generator

Générateur automatique de sous-titres français pour vidéos d'anime.

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

# Créer un fichier .env
echo "GROQ_API_KEY=votre_clé_ici" > .env

# Lancer l'application
streamlit run app.py
```

## 📋 Technologies

- **Streamlit** : Interface web
- **Whisper** : Transcription audio → texte
- **Groq (Llama 3)** : Traduction JA → FR
- **FFmpeg** : Traitement vidéo/audio

## 📝 Licence

MIT
