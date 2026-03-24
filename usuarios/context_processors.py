# usuarios/context_processors.py
def user_permissions(request):
    """
    Agrega los permisos del usuario al contexto de todos los templates
    """
    if not hasattr(request.user, 'is_authenticated') or not request.user.is_authenticated:
        return {'user_permissions': {}, 'user_rol': None}
    
    user = request.user
    rol_nombre = user.id_rol.nombre_rol if hasattr(user, 'id_rol') and user.id_rol else None
    
    # Matriz de permisos por rol
    permisos = {
        'can_view_inventario': rol_nombre in ['GERENTE', 'JEFE LOGISTICO', 'AUXILIAR DE BODEGA', 'ASESOR COMERCIAL'],
        'can_view_ventas': rol_nombre in ['GERENTE', 'ASESOR COMERCIAL'],
        'can_view_compras': rol_nombre in ['GERENTE', 'ASESOR COMERCIAL'],
        'can_view_produccion': rol_nombre in ['GERENTE', 'JEFE LOGISTICO', 'AUXILIAR DE BODEGA'],
        'can_view_clientes': rol_nombre in ['GERENTE', 'ASESOR COMERCIAL', 'JEFE LOGISTICO', 'AUXILIAR DE BODEGA'],
        'can_view_pedidos': rol_nombre in ['GERENTE', 'ASESOR COMERCIAL', 'JEFE LOGISTICO', 'AUXILIAR DE BODEGA'],
        'can_view_cotizaciones': rol_nombre in ['GERENTE', 'ASESOR COMERCIAL'],
        'can_view_reportes': rol_nombre in ['GERENTE'],
        'can_view_usuarios': rol_nombre in ['GERENTE'],
        'can_view_dashboard': rol_nombre != 'CLIENTE',
    }
    
    return {
        'user_permissions': permisos,
        'user_rol': rol_nombre,
        'user_nombre': f"{user.nombres} {user.apellidos}" if hasattr(user, 'nombres') else ''
    }