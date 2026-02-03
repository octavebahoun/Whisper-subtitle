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

# Port exposé par défaut pour Streamlit
EXPOSE 7860

# Configuration de Streamlit pour fonctionner correctement dans Docker sur HF
ENV STREAMLIT_SERVER_PORT=7860
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Lancement de l'application avec les réglages CORS pour Hugging Face
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
