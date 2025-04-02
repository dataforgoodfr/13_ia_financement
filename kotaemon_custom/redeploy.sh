#!/bin/bash

# 1. Arrêt et nettoyage
docker compose down --timeout 2

# 2. Synchronisation Git
git pull origin main
git status
git diff HEAD

# 3. Reconstruction Docker
docker compose build --no-cache --progress=plain

# 4. Redémarrage avec logging
docker compose up -d
docker compose logs -f kotaemon_custom