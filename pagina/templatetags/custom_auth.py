from django import template

register = template.Library()


@register.filter(name='has_role')
def has_role(user, roles_str):
    """
    Verifica si el usuario tiene alguno de los roles especificados.
    Uso: {% if user|has_role:'ADMIN,Gerente' %}
    """
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    
    roles = [r.strip() for r in roles_str.split(',')]
    
    # Verificar por campo personalizado 'rol'
    if hasattr(user, 'rol') and user.rol in roles:
        return True
    
    # Verificar por grupos de Django (solo si el objeto los soporta)
    try:
        user_groups = user.groups.values_list('name', flat=True)
        if any(role in user_groups for role in roles):
            return True
    except Exception:
        pass
    
    is_super = getattr(user, 'is_superuser', False)
    is_staff = getattr(user, 'is_staff', False)
    if 'ADMIN' in roles and (is_super or is_staff):
        return True
    
    return False


@register.filter(name='range')
def make_range(value):
    try:
        return range(int(value))
    except (ValueError, TypeError, AttributeError):
        return range(0)