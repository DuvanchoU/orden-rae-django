from django import template
from decimal import Decimal

register = template.Library()


@register.filter(name='split')
def split(value, arg):
    """
    Divide una cadena por el separador indicado.
    Uso: {{ "a,b,c"|split:"," }}
    """
    return value.split(arg)


@register.filter(name='replace')
def replace(value, arg):
    """
    Reemplaza caracteres en una cadena.
    Uso: {{ "hola-mundo"|replace:"-/ " }}
    """
    try:
        old, new = arg.split('/')
        return str(value).replace(old, new)
    except (ValueError, AttributeError):
        return value


@register.filter(name='has_role')
def has_role(user, roles_str):
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    roles = [r.strip() for r in roles_str.split(',')]
    if hasattr(user, 'rol') and user.rol in roles:
        return True
    try:
        user_groups = user.groups.values_list('name', flat=True)
        if any(role in user_groups for role in roles):
            return True
    except Exception:
        pass
    if 'ADMIN' in roles and (getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False)):
        return True
    return False


@register.filter(name='range')
def make_range(value):
    try:
        return range(int(value))
    except (ValueError, TypeError, AttributeError):
        return range(0)


@register.filter(name='add_percent')
def add_percent(value, percent):
    """
    Incrementa un valor numérico en el porcentaje indicado.
    Uso: {{ prod.precio_actual|add_percent:20 }}
    """
    try:
        return Decimal(str(value)) * (1 + Decimal(str(percent)) / 100)
    except Exception:
        return value