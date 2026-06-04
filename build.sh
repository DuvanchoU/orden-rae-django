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

# Crear superusuario automáticamente
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@ordenrae.com',
        password='admin123'
    )
    print("Superusuario creado: admin / admin123")
else:
    print("El superusuario ya existe")
EOF