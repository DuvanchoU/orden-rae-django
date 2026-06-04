#!/usr/bin/env bash
# Exit on error
set -o errexit

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# Aplicar migraciones
python manage.py migrate

# Recopilar archivos estáticos
python manage.py collectstatic --no-input

# Crear superusuario (opcional)
# python manage.py createsuperuser