# 📁 pagina/templatetags/custom_auth.py
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
    
    # Verificar por grupos de Django
    try:
        user_groups = user.groups.values_list('name', flat=True)
        if any(role in user_groups for role in roles):
            return True
    except:
        pass
    
    # Verificar ADMIN por is_superuser/is_staff
    if 'ADMIN' in roles and (user.is_superuser or user.is_staff):
        return True
    
    return False


@register.filter(name='range')
def make_range(value):
    """
    Genera un rango de números para loops.
    Uso: {% for i in 5|range %} → 0,1,2,3,4
    """
    try:
        return range(int(value))
    except (ValueError, TypeError, AttributeError):
        return range(0)