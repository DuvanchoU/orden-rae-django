from django import template

register = template.Library()


@register.filter(name='has_role')
def has_role(user, roles_str):
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False

    roles = [r.strip() for r in roles_str.split(',')]

    # Primero verificar el atributo 'rol' si existe
    try:
        rol_usuario = user.rol  # puede lanzar AttributeError si es PropertyMock
        if rol_usuario in roles:
            return True
        # Si tiene 'rol' pero no coincide, NO seguir al fallback de superuser
        return False
    except AttributeError:
        pass

    # Sin atributo 'rol': verificar grupos
    try:
        user_groups = list(user.groups.values_list('name', flat=True))
        if any(role in user_groups for role in roles):
            return True
    except Exception:
        pass

    # Último recurso: superuser/staff para rol ADMIN
    if 'ADMIN' in roles and (getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False)):
        return True

    return False


@register.filter(name='range')
def make_range(value):
    try:
        return range(int(value))
    except (ValueError, TypeError, AttributeError):
        return range(0)