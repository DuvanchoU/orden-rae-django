def user_permissions(request):
    user = getattr(request, 'user', None)

    # Sin usuario o no autenticado
    if not user or not getattr(user, 'is_authenticated', False):
        return {
            'user_permissions': {},
            'user_rol': None,
            'user_nombre': '',
            'is_cliente': False,
            'is_staff_user': False,
        }

    is_cliente    = hasattr(user, 'id_cliente')
    is_staff_user = hasattr(user, 'id_usuario')

    # Cliente
    if is_cliente:
        return {
            'user_permissions': {
                'can_view_inventario':   False,
                'can_view_ventas':       False,
                'can_view_compras':      False,
                'can_view_produccion':   False,
                'can_view_clientes':     False,
                'can_view_pedidos':      False,
                'can_view_cotizaciones': False,
                'can_view_reportes':     False,
                'can_view_usuarios':     False,
                'can_view_dashboard':    False,
            },
            'user_rol':      'CLIENTE',
            'user_nombre':   user.get_nombre_completo() if hasattr(user, 'get_nombre_completo') else getattr(user, 'nombre', ''),
            'is_cliente':    True,
            'is_staff_user': False,
        }

    # Staff
    if is_staff_user:
        rol_nombre = user.id_rol.nombre_rol if getattr(user, 'id_rol', None) else None

        permisos = {
            'can_view_inventario':   rol_nombre in ['GERENTE', 'JEFE LOGISTICO', 'AUXILIAR DE BODEGA', 'ASESOR COMERCIAL'],
            'can_view_ventas':       rol_nombre in ['GERENTE', 'ASESOR COMERCIAL'],
            'can_view_compras':      rol_nombre in ['GERENTE'],
            'can_view_produccion':   rol_nombre in ['GERENTE', 'JEFE LOGISTICO', 'AUXILIAR DE BODEGA'],
            'can_view_clientes':     rol_nombre in ['GERENTE', 'ASESOR COMERCIAL', 'JEFE LOGISTICO', 'AUXILIAR DE BODEGA'],
            'can_view_pedidos':      rol_nombre in ['GERENTE', 'ASESOR COMERCIAL', 'JEFE LOGISTICO', 'AUXILIAR DE BODEGA'],
            'can_view_cotizaciones': rol_nombre in ['GERENTE', 'ASESOR COMERCIAL'],
            'can_view_reportes':     rol_nombre in ['GERENTE'],
            'can_view_usuarios':     rol_nombre in ['GERENTE'],
            'can_view_dashboard':    rol_nombre in ['GERENTE', 'ASESOR COMERCIAL', 'JEFE LOGISTICO', 'AUXILIAR DE BODEGA'],
        }

        return {
            'user_permissions': permisos,
            'user_rol':      rol_nombre or 'SIN_ROL',
            'user_nombre':   user.get_nombre_completo() if hasattr(user, 'get_nombre_completo') else f"{getattr(user, 'nombres', '')} {getattr(user, 'apellidos', '')}".strip(),
            'is_cliente':    False,
            'is_staff_user': True,
        }

    # Fallback — usuario autenticado pero sin tipo reconocido
    return {
        'user_permissions': {},
        'user_rol': None,
        'user_nombre': '',
        'is_cliente': False,
        'is_staff_user': False,
    }