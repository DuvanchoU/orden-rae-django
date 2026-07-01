from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.utils import timezone

from ventas.models import Clientes


class MySocialAccountAdapter(DefaultSocialAccountAdapter):

    def pre_social_login(self, request, sociallogin):
        """
        Se ejecuta SIEMPRE que un usuario inicia sesión con Google,
        exista o no exista previamente.
        """

        datos = sociallogin.account.extra_data

        email = datos.get("email")
        nombre = datos.get("given_name", "")
        apellido = datos.get("family_name", "")

        if not email:
            return

        cliente, creado = Clientes.objects.get_or_create(
            email=email,
            defaults={
                "nombre": nombre or "Usuario",
                "apellido": apellido,
                "estado": "ACTIVO",
                "email_verificado": True,
                "fecha_registro": timezone.now(),
                "created_at": timezone.now(),
                "updated_at": timezone.now(),
                "ultimo_login": timezone.now(),
                "last_login": timezone.now(),
            }
        )

        if not creado:
            cliente.nombre = nombre or cliente.nombre
            cliente.apellido = apellido or cliente.apellido
            cliente.ultimo_login = timezone.now()
            cliente.last_login = timezone.now()
            cliente.save()

        # Crear las mismas variables de sesión que usa tu login tradicional
        request.session["cliente_auth"] = True
        request.session["cliente_id"] = cliente.id_cliente
        request.session["cliente_nombre"] = cliente.get_nombre_completo()
        request.session["cliente_email"] = cliente.email