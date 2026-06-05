"""
Script para configurar OAuth 2.0 (Google) en Django
Uso: python setup_oauth.py
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

# ============================================
# REEMPLAZA ESTOS VALORES CON TUS CREDENCIALES REALES
# ============================================
GOOGLE_CLIENT_ID = '952277600463-ssice2e2g3en1qar7ljpcqftgfudegsl.apps.googleusercontent.com'  
GOOGLE_SECRET = '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' 
# ============================================

def setup_oauth():
    print("🔧 Configurando OAuth 2.0 para Google...")
    print("=" * 50)
    
    # 1. Actualizar el Site
    try:
        site = Site.objects.get(id=1)
        site.domain = '127.0.0.1:8000'
        site.name = 'localhost'
        site.save()
        print(f"Site actualizado: {site.domain}")
    except Exception as e:
        print(f"Error al actualizar el Site: {e}")
        return
    
    # 2. Crear o actualizar el SocialApp de Google
    try:
        app, created = SocialApp.objects.get_or_create(
            provider='google',
            defaults={
                'name': 'Google OAuth',
                'client_id': GOOGLE_CLIENT_ID,
                'secret': GOOGLE_SECRET,
            }
        )
        
        # Si ya existía, actualizar los valores
        if not created:
            app.client_id = GOOGLE_CLIENT_ID
            app.secret = GOOGLE_SECRET
            app.name = 'Google OAuth'
            app.save()
            print(f"SocialApp de Google ACTUALIZADO")
        else:
            print(f"SocialApp de Google CREADO")
        
        # 3. Vincular el site al SocialApp
        app.sites.add(site)
        print(f"Site vinculado al SocialApp")
        
        # 4. Mostrar configuración final
        print("\n" + "=" * 50)
        print("Configuración final:")
        print(f"   Provider: {app.provider}")
        print(f"   Name: {app.name}")
        print(f"   Client ID: {app.client_id[:20]}...")
        print(f"   Sites: {list(app.sites.all())}")
        print("=" * 50)
        print("\n ¡Configuración completada!")
        print("🌐 Ve a http://127.0.0.1:8000/login/ y prueba el botón de Google")
        
    except Exception as e:
        print(f" Error al crear el SocialApp: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    setup_oauth()