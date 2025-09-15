# Utilise une image de base Ubuntu, reconnue pour sa stabilité.
FROM ubuntu:22.04

# Rend l'installation non interactive pour éviter les blocages.
ENV DEBIAN_FRONTEND=noninteractive

# Définit un répertoire de travail pour une meilleure organisation.
WORKDIR /app

# --- Installation des dépendances du système ---
RUN apt-get update && apt-get install -y \
    software-properties-common \
    gnupg \
    wget \
    python3 \
    python3-pip \
    python3-dev \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# --- Ajout du dépôt de QGIS pour obtenir les paquets officiels ---
# Ajoute la clé GPG et le dépôt officiel de QGIS pour Ubuntu.
RUN wget -O - https://qgis.org/downloads/qgis-archive-keyring.gpg | gpg --dearmor | tee /etc/apt/keyrings/qgis-archive-keyring.gpg > /dev/null
RUN echo "deb [signed-by=/etc/apt/keyrings/qgis-archive-keyring.gpg] https://qgis.org/ubuntu jammy main" | tee /etc/apt/sources.list.d/qgis.list
RUN echo "deb-src [signed-by=/etc/apt/keyrings/qgis-archive-keyring.gpg] https://qgis.org/ubuntu jammy main" | tee -a /etc/apt/sources.list.d/qgis.list

# --- Installation des paquets QGIS ---
# Rend la commande plus résiliente aux erreurs de téléchargement
# et installe les paquets essentiels pour le mode headless.
RUN apt-get update || (sleep 10 && apt-get update) \
    && apt-get install -y \
    qgis-server \
    qgis-plugin-grass \
    libgdal-dev \
    python3-qgis \
    qgis-providers \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- Configuration de l'environnement Python ---
# Indique à QGIS où trouver ses bibliothèques (obligatoire en mode headless).
ENV QGIS_PREFIX_PATH="/usr"

# Copier ton code API dans /app
COPY . /app

# Installer dépendances Python
RUN pip3 install --no-cache-dir -r requirements.txt

# Démarrage de l’API
CMD ["python3", "manage.py", "runserver", "0.0.0.0:10000"]
