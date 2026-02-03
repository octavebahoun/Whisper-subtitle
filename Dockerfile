FROM python:3.12-slim

# Installation de FFmpeg, Sox et des outils système nécessaires
RUN apt-get update && apt-get install -y \
    ffmpeg \
    sox \
    libsox-fmt-all \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# On s'assure que pip est à jour
RUN pip install --upgrade pip

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie de tout le code du projet
COPY . .

# Création du dossier temporaire pour les uploads avec les droits d'écriture
RUN mkdir -p uploads && chmod 777 uploads

# Création du fichier de config Streamlit robuste pour Mobile + Hugging Face
RUN mkdir -p .streamlit && echo "\
[server]\n\
maxUploadSize = 1024\n\
enableCORS = false\n\
enableXsrfProtection = false\n\
enableWebsocketCompression = false\n\
socketTimeout = 3600\n\
\n\
[browser]\n\
gatherUsageStats = false\n\
" > .streamlit/config.toml

# Port exposé par défaut pour Streamlit
EXPOSE 7860

# Configuration de Streamlit pour fonctionner correctement dans Docker sur HF
ENV STREAMLIT_SERVER_PORT=7860
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Lancement de l'application (les configs sont dans .streamlit/config.toml)
CMD ["streamlit", "run", "app.py"]
