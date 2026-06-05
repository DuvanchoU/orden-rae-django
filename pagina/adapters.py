from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User
from ventas.models import Clientes
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Adaptador personalizado para OAuth 2.0
    Crea un User de Django y lo vincula con un Cliente
    """
    
    def is_open_for_signup(self, request, sociallogin):
        """Permitir registro vía OAuth"""
        return True
    
    def pre_social_login(self, request, sociallogin):
        """
        Antes de procesar el login social:
        Si el email ya existe en User, vincular cuenta
        """
        email = sociallogin.account.extra_data.get('email')
        if not email:
            return
        
        logger.info(f"OAuth pre_social_login: {email}")
            
        try:
            # Buscar si ya existe un User con ese email
            user_existente = User.objects.get(email__iexact=email)
            sociallogin.connect(request, user_existente)
            logger.info(f"User existente vinculado: {user_existente.email}")
        except User.DoesNotExist:
            logger.info(f"No existe User para {email}, se creará en save_user")
    
    def save_user(self, request, sociallogin, form=None):
        """
        Crear User de Django y Cliente vinculado
        """
        data = sociallogin.account.extra_data
        
        email = data.get('email', '')
        nombre = data.get('given_name') or data.get('first_name') or 'Cliente'
        apellido = data.get('family_name') or data.get('last_name') or 'OAuth'
        
        logger.info(f"OAuth save_user: Creando para {email}")
        
        # Crear o obtener User de Django
        # Buscar User existente (tomar el más reciente si hay duplicados)
        users_with_email = User.objects.filter(email__iexact=email).order_by('-id')
        if users_with_email.exists():
            user = users_with_email.first()
            logger.info(f"User existente: {user.email} (ID: {user.id})")
        else:
            # Crear nuevo User
            username = email.split('@')[0]
            # Asegurar que el username sea único
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=nombre,
                last_name=apellido,
                password=None  # No tiene contraseña (solo OAuth)
            )
            user.is_active = True
            user.save()
            logger.info(f"Nuevo User creado: {user.username} ({user.email})")
        
        # Crear o actualizar Cliente vinculado
        try:
            cliente = Clientes.objects.get(email__iexact=email, deleted_at__isnull=True)
            logger.info(f"Cliente existente: {cliente.email}")
            # Actualizar último login
            cliente.ultimo_login = timezone.now()
            cliente.save(update_fields=['ultimo_login'])
        except Clientes.DoesNotExist:
            # Crear nuevo Cliente
            cliente = Clientes.objects.create(
                nombre=nombre,
                apellido=apellido,
                email=email,
                estado='ACTIVO',
                email_verificado=True,
                fecha_registro=timezone.now(),
                ultimo_login=timezone.now(),
            )
            logger.info(f"Nuevo Cliente creado: ID {cliente.id_cliente} - {cliente.nombre} {cliente.apellido}")
        
        # Asignar el User al sociallogin
        sociallogin.user = user
        
        return user
    
    def get_login_redirect_url(self, request):
        """Redirigir al home de la web tras login OAuth"""
        return '/'