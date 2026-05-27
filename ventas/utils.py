# ventas/utils.py
import hashlib
import secrets
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def generar_token_seguro(longitud=32):
    """Genera un token criptográficamente seguro"""
    return secrets.token_urlsafe(longitud)

def generar_token_sha256(valor_base):
    """Genera token SHA256 para compatibilidad con el sistema"""
    return hashlib.sha256(valor_base.encode()).hexdigest()

def enviar_email_verificacion(cliente):
    """Envía email de verificación de cuenta"""
    
    # Generar token único
    token = generar_token_seguro()
    cliente.token_verificacion = token
    cliente.token_verificacion_expira = timezone.now() + timedelta(hours=24)
    cliente.save(update_fields=['token_verificacion', 'token_verificacion_expira'])
    
    # Generar enlace de verificación
    enlace_verificacion = f"{settings.SITE_URL}/pagina/verificar-email/{token}/"
    
    # Contexto para el template
    context = {
        'cliente': cliente,
        'enlace_verificacion': enlace_verificacion,
        'nombre_empresa': 'La Super Bodega del Mueble',
        'anio': timezone.now().year,
    }
    
    # Renderizar templates
    html_message = render_to_string('emails/verificacion_email.html', context)
    plain_message = strip_tags(html_message)
    
    # Enviar email
    send_mail(
        subject='Verifica tu cuenta - La Super Bodega del Mueble',
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[cliente.email],
        html_message=html_message,
        fail_silently=False,
    )
    
    return True

def enviar_email_reset_password(cliente):
    """Envía email para recuperar contraseña"""
    
    # Generar token único
    token = generar_token_seguro()
    cliente.token_reset_password = token
    cliente.token_reset_password_expira = timezone.now() + timedelta(hours=1)
    cliente.save(update_fields=['token_reset_password', 'token_reset_password_expira'])
    
    # Generar enlace de recuperación
    enlace_reset = f"{settings.SITE_URL}/pagina/reset-password/{token}/"
    
    # Contexto para el template
    context = {
        'cliente': cliente,
        'enlace_reset': enlace_reset,
        'nombre_empresa': 'La Super Bodega del Mueble',
        'horas_validez': 1,
        'anio': timezone.now().year,
    }
    
    # Renderizar templates
    html_message = render_to_string('emails/reset_password_email.html', context)
    plain_message = strip_tags(html_message)
    
    # Enviar email
    send_mail(
        subject='Recuperar contraseña - La Super Bodega del Mueble',
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[cliente.email],
        html_message=html_message,
        fail_silently=False,
    )
    
    return True

def validar_token_verificacion(token):
    """Valida token de verificación de email"""
    from ventas.models import Clientes
    
    try:
        cliente = Clientes.objects.get(
            token_verificacion=token,
            token_verificacion_expira__gt=timezone.now(),
            deleted_at__isnull=True
        )
        return cliente
    except Clientes.DoesNotExist:
        return None

def validar_token_reset_password(token):
    """Valida token de recuperación de contraseña"""
    from ventas.models import Clientes
    
    try:
        cliente = Clientes.objects.get(
            token_reset_password=token,
            token_reset_password_expira__gt=timezone.now(),
            deleted_at__isnull=True
        )
        return cliente
    except Clientes.DoesNotExist:
        return None