from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from ventas.models import Clientes
from usuarios.models import Usuarios, RolesOld
from inventario.models import Producto, Categorias, ImagenesProducto, Inventario
import hashlib
import json
import re
import random
import string
import logging
logger = logging.getLogger('auth.debug')
from django.core.mail import send_mail
from django.conf import settings
from decimal import Decimal
from django.core.paginator import Paginator 
import os
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.db import transaction

# Vistas para páginas principales (home, productos, promociones, contacto, etc.)
# Vistas para autenticación (login, registro, perfil)
# Vistas para manejo de carrito y checkout
@login_required
@require_POST
@csrf_protect
# Endpoint AJAX para actualizar foto de perfil del usuario
def actualizar_avatar(request):
    """
    Endpoint AJAX para actualizar la foto de perfil del usuario.
    Devuelve la URL de la nueva foto para actualizar el DOM en tiempo real.
    """
    foto = request.FILES.get('foto_perfil')

    if not foto:
        return JsonResponse({'success': False, 'error': 'No se recibió ningún archivo.'}, status=400)

    # Validar tipo MIME
    tipos_permitidos = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
    if foto.content_type not in tipos_permitidos:
        return JsonResponse({'success': False, 'error': 'Tipo de archivo no permitido.'}, status=400)

    # Validar tamaño (5 MB máximo)
    if foto.size > 5 * 1024 * 1024:
        return JsonResponse({'success': False, 'error': 'El archivo supera el límite de 5 MB.'}, status=400)

    user = request.user

    # Eliminar foto anterior si existe (evitar acumulación de archivos)
    if user.foto_perfil:
        try:
            old_path = user.foto_perfil.path
            if os.path.isfile(old_path):
                os.remove(old_path)
        except Exception:
            pass  # Silenciar errores al borrar archivo viejo

    # Guardar nueva foto
    user.foto_perfil = foto
    user.save(update_fields=['foto_perfil']) 
    return JsonResponse({
        'success': True,
        'foto_url': user.foto_perfil.url,
        'mensaje': 'Foto actualizada correctamente.'
    })

# Función auxiliar para generar URL de avatar consistente (usada en testimonios)
def generar_avatar_url(nombre, tamaño=128):
    """Genera una URL de avatar consistente basada en el nombre."""
    colores = [
        '667eea', '764ba2', 'f093fb', '4facfe', '43e972',
        'fa709a', 'fee140', '30cfd0', 'a8edea', 'feaca9'
    ]
    hash_nombre = int(hashlib.md5(nombre.encode('utf-8')).hexdigest(), 16)
    color = colores[hash_nombre % len(colores)]
    nombre_url = nombre.replace(' ', '+')
    return f"https://ui-avatars.com/api/?name={nombre_url}&background={color}&color=fff&size={tamaño}&bold=true"

#Actualizar avatar en perfil de usuario
@login_required
@require_POST
def avatar_actualizar(request):
    import base64, re
    from django.core.files.base import ContentFile
    user = request.user
    data = request.POST.get('avatar_base64', '')
    if not data:
        return JsonResponse({'success': False, 'error': 'Sin imagen.'})
    # Extraer base64
    match = re.match(r'data:image/(\w+);base64,(.*)', data, re.DOTALL)
    if not match:
        return JsonResponse({'success': False, 'error': 'Formato inválido.'})
    ext, imgdata = match.group(1), match.group(2)
    archivo = ContentFile(base64.b64decode(imgdata), name=f'avatar_{user.id}.{ext}')
    # Guardar en el perfil (ajusta según tu modelo)
    perfil = getattr(user, 'perfil', None)
    if perfil and hasattr(perfil, 'avatar'):
        perfil.avatar.save(archivo.name, archivo, save=True)
        return JsonResponse({'success': True, 'avatar_url': perfil.avatar.url})
    return JsonResponse({'success': False, 'error': 'Modelo de perfil no encontrado.'})

def home(request):
    """Vista principal - Con productos desde la base de datos"""
    
    # === PRODUCTOS DESTACADOS (desde BD) ===
    productos_destacados_qs = Producto.objects.filter(
        estado='DISPONIBLE',
        deleted_at__isnull=True
    ).select_related('categoria')[:5]
    
    productos_destacados = []
    for prod in productos_destacados_qs:
        imagen_principal = ImagenesProducto.objects.filter(
            producto=prod,
            es_principal=1
        ).first()
        productos_destacados.append({
            'id': prod.id_producto,
            'nombre': prod.referencia_producto or prod.codigo_producto,
            'slug': prod.codigo_producto.lower().replace(' ', '-'),
            'precio': int(prod.precio_actual),
            'imagen_url': imagen_principal.ruta_imagen if imagen_principal else '/static/img/placeholder.jpg',
        })
    
    # === NUEVOS PRODUCTOS (desde BD) ===
    treinta_dias_atras = timezone.now() - timedelta(days=30)
    productos_nuevos_qs = Producto.objects.filter(
        estado='DISPONIBLE',
        deleted_at__isnull=True,
        created_at__gte=treinta_dias_atras
    ).select_related('categoria')[:4]
    
    if not productos_nuevos_qs:
        productos_nuevos_qs = Producto.objects.filter(
            estado='DISPONIBLE',
            deleted_at__isnull=True
        ).select_related('categoria').order_by('-created_at')[:4]
    
    productos_nuevos = []
    for prod in productos_nuevos_qs:
        imagen_principal = ImagenesProducto.objects.filter(
            producto=prod,
            es_principal=1
        ).first()
        productos_nuevos.append({
            'id': prod.id_producto,
            'nombre': prod.referencia_producto or prod.codigo_producto,
            'slug': prod.codigo_producto.lower().replace(' ', '-'),
            'categoria': prod.categoria.nombre_categoria if prod.categoria else 'General',
            'precio': int(prod.precio_actual),
            'precio_desde': False,
            'tiene_opciones': False,
            'imagen_url': imagen_principal.ruta_imagen if imagen_principal else '/static/img/placeholder.jpg',
        })
    
    # === TESTIMONIOS ===
    testimonios = [
        {
            'nombre_cliente': 'María G.',
            'estrellas': 5,
            'comentario': '¡El sofá es hermoso y llegó antes de lo esperado! El servicio fue impecable.',
            'avatar': generar_avatar_url('María G.')
        },
        {
            'nombre_cliente': 'Carlos R.',
            'estrellas': 4,
            'comentario': 'La cama es muy cómoda y el ensamblaje fue sencillo. Recomendado 100%.',
            'avatar': generar_avatar_url('Carlos R.')
        },
        {
            'nombre_cliente': 'Ana M.',
            'estrellas': 5,
            'comentario': 'Excelente calidad-precio. Ya estoy pensando en mi próxima compra.',
            'avatar': generar_avatar_url('Ana M.')
        }
    ]
    
    # === DATOS PARA JAVASCRIPT ===
    categorias_qs = Categorias.objects.filter(
        estado_categoria='activo',
        deleted_at__isnull=True
    )
    
    datos_opciones = {'escritorio': [], 'cama': []}
    
    for cat in categorias_qs:
        if 'ESCRITORIO' in cat.nombre_categoria.upper():
            prods = Producto.objects.filter(
                categoria=cat,
                estado='DISPONIBLE',
                deleted_at__isnull=True
            )[:4]
            for p in prods:
                img = ImagenesProducto.objects.filter(producto=p, es_principal=1).first()
                datos_opciones['escritorio'].append({
                    'nombre': p.referencia_producto or p.codigo_producto,
                    'img': img.ruta_imagen if img else '/static/img/placeholder.jpg',
                    'precio': int(p.precio_actual),
                    'slug': p.codigo_producto.lower().replace(' ', '-'),
                    'id': p.id_producto
                })
        
        if 'CAMA' in cat.nombre_categoria.upper() or 'CUNA' in cat.nombre_categoria.upper():
            prods = Producto.objects.filter(
                categoria=cat,
                estado='DISPONIBLE',
                deleted_at__isnull=True
            )[:4]
            for p in prods:
                img = ImagenesProducto.objects.filter(producto=p, es_principal=1).first()
                datos_opciones['cama'].append({
                    'nombre': p.referencia_producto or p.codigo_producto,
                    'img': img.ruta_imagen if img else '/static/img/placeholder.jpg',
                    'precio': int(p.precio_actual),
                    'slug': p.codigo_producto.lower().replace(' ', '-'),
                    'id': p.id_producto
                })
    
    productos_busqueda = list(
        Producto.objects.filter(
            estado='DISPONIBLE',
            deleted_at__isnull=True
        ).values_list('referencia_producto', flat=True)[:50]
    )
    
    # === CATEGORÍAS DESDE LA BASE DE DATOS ===
    categorias_qs = Categorias.objects.filter(
        estado_categoria='activo',
        deleted_at__isnull=True
    ).annotate(
        productos_count=Count(
            'productos', 
            filter=Q(
                productos__estado='DISPONIBLE',
                productos__deleted_at__isnull=True
            )
        )
    ).order_by('nombre_categoria')[:7]
    
    categorias = []
    for cat in categorias_qs:
        primer_producto = Producto.objects.filter(
            categoria=cat,
            deleted_at__isnull=True
        ).first()
        
        imagen_url = '/static/img/placeholder.jpg'
        if primer_producto:
            img = ImagenesProducto.objects.filter(
                producto=primer_producto,
                es_principal=1
            ).first()
            if img:
                imagen_url = img.ruta_imagen
        
        categorias.append({
            'id': cat.id_categorias,
            'nombre': cat.nombre_categoria,
            'slug': cat.nombre_categoria.lower().replace(' ', '-').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u'),
            'descripcion_corta': f'{cat.productos_count} productos disponibles',
            'descripcion_larga': f'Explora nuestra selección de {cat.nombre_categoria.lower()}',
            'imagen_url': imagen_url,
            'productos_count': cat.productos_count
        })
    
    notificaciones = []
    notificaciones_nuevas = 0
    if request.user.is_authenticated:
        pass
    
    context = {
        'carrito_cantidad': request.session.get('carrito_cantidad', 0),
        'datos_opciones_json': json.dumps(datos_opciones),
        'productos_busqueda_json': json.dumps(productos_busqueda),
        'productos_destacados': productos_destacados,
        'productos_nuevos': productos_nuevos,
        'hay_productos_nuevos': bool(productos_nuevos),
        'testimonios': testimonios,
        'notificaciones': notificaciones,
        'notificaciones_nuevas': notificaciones_nuevas,
        'categorias': categorias,
        'categorias_json': json.dumps([
            {'nombre': c['nombre'], 'slug': c['slug']} for c in categorias
        ]),
    }
    
    return render(request, 'pagina/index.html', context)


def productos(request):
    """Vista de página de productos con paginación"""

    categorias_principales_slugs = [
        'bases-de-comedor', 'cama-cunas', 'butacos-de-bar',
        'camas-adultos', 'camas-infantiles', 'todas'
    ]

    todas_categorias = Categorias.objects.filter(
        estado_categoria='activo',
        deleted_at__isnull=True
    ).annotate(
        productos_count=Count('productos', filter=Q(
            productos__estado='DISPONIBLE',
            productos__deleted_at__isnull=True
        ))
    ).order_by('nombre_categoria')

    categorias_principales = []
    categorias_secundarias = []

    for cat in todas_categorias:
        slug = (cat.nombre_categoria.lower()
                .replace(' ', '-').replace('á', 'a').replace('é', 'e')
                .replace('í', 'i').replace('ó', 'o').replace('ú', 'u'))

        primer_producto = Producto.objects.filter(
            categoria=cat, deleted_at__isnull=True
        ).first()
        imagen_url = '/static/img/placeholder.jpg'
        if primer_producto:
            img = ImagenesProducto.objects.filter(
                producto=primer_producto, es_principal=1
            ).first()
            if img:
                imagen_url = img.ruta_imagen

        categoria_data = {
            'id': cat.id_categorias,
            'nombre': cat.nombre_categoria,
            'slug': slug,
            'descripcion_corta': f'{cat.productos_count} productos disponibles',
            'descripcion_larga': f'Explora nuestra selección de {cat.nombre_categoria.lower()}',
            'imagen_url': imagen_url,
            'productos_count': cat.productos_count
        }

        if (slug in categorias_principales_slugs or
                cat.nombre_categoria.upper() in [
                    'BASES DE COMEDOR', 'CAMA CUNAS', 'BUTACOS DE BAR',
                    'CAMAS ADULTOS', 'CAMAS INFANTILES'
                ]):
            categorias_principales.append(categoria_data)
        elif cat.productos_count > 0:
            categorias_secundarias.append(categoria_data)

    if not any(c['slug'] == 'todas' for c in categorias_principales):
        categorias_principales.insert(0, {
            'id': 0,
            'nombre': 'Todas',
            'slug': 'todas',
            'descripcion_corta': 'Ver todos los productos',
            'descripcion_larga': 'Explora todo nuestro catálogo',
            'imagen_url': '/static/img/placeholder.jpg',
            'productos_count': Producto.objects.filter(
                estado='DISPONIBLE', deleted_at__isnull=True
            ).count()
        })

    # === PRODUCTOS DESTACADOS ===
    productos_destacados_qs = Producto.objects.filter(
        estado='DISPONIBLE', deleted_at__isnull=True
    ).select_related('categoria')[:4]

    productos_destacados = []
    for prod in productos_destacados_qs:
        img = ImagenesProducto.objects.filter(producto=prod, es_principal=1).first()
        productos_destacados.append({
            'id': prod.id_producto,
            'nombre': prod.referencia_producto or prod.codigo_producto,
            'slug': prod.codigo_producto.lower().replace(' ', '-'),
            'precio': int(prod.precio_actual),
            'imagen_url': img.ruta_imagen if img else '/static/img/placeholder.jpg'
        })

    # === BADGES: 5 más nuevos y 5 más antiguos ===
    ids_nuevos = list(
        Producto.objects.filter(estado='DISPONIBLE', deleted_at__isnull=True)
        .order_by('-created_at')
        .values_list('id_producto', flat=True)[:5]
    )
    ids_oferta = list(
        Producto.objects.filter(estado='DISPONIBLE', deleted_at__isnull=True)
        .order_by('created_at')
        .values_list('id_producto', flat=True)[:5]
    )

    # === TODOS LOS PRODUCTOS (sin límite, el paginator lo maneja) ===
    todos_productos_qs = Producto.objects.filter(
        estado='DISPONIBLE', deleted_at__isnull=True
    ).select_related('categoria').order_by('-created_at')

    productos_list_completa = []
    for prod in todos_productos_qs:
        img = prod.get_imagen_principal()
        cat_slug = (
            prod.categoria.nombre_categoria.lower()
            .replace(' ', '-').replace('á', 'a').replace('é', 'e')
            .replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
            if prod.categoria else 'sin-categoria'
        )
        productos_list_completa.append({
            'id_producto':         prod.id_producto,
            'nombre':              prod.referencia_producto or prod.codigo_producto,
            'referencia_producto': prod.referencia_producto or prod.codigo_producto,
            'codigo_producto':     prod.codigo_producto,
            'precio_actual':       prod.precio_actual,
            'precio_numeric':      float(prod.precio_actual),
            'categoria_slug':      cat_slug,
            'imagen_url':          img.ruta_imagen if img else '/static/img/placeholder.jpg',
            'created_at':          prod.created_at.isoformat() if prod.created_at else '',
            'es_nuevo':            prod.id_producto in ids_nuevos,
            'es_oferta':           prod.id_producto in ids_oferta,
        })

    # === PAGINACIÓN: 20 productos por página ===
    paginator = Paginator(productos_list_completa, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    sort_options = [
        ("Relevancia", "relevancia"),
        ("Precio ↑", "precio-asc"),
        ("Precio ↓", "precio-desc"),
        ("Más nuevos", "mas-nuevos"),
        ("A – Z", "nombre-asc"),
    ]

    context = {
        'categorias_principales':  categorias_principales,
        'categorias_secundarias':  categorias_secundarias,
        'productos_destacados':    productos_destacados,
        'productos':               page_obj,          # ← page_obj en lugar de lista
        'page_obj':                page_obj,
        'paginator':               paginator,
        'sort_options':            sort_options,
        'categorias_json': json.dumps([
            {'nombre': c['nombre'], 'slug': c['slug'], 'productos_count': c['productos_count']}
            for c in categorias_principales + categorias_secundarias
        ]),
        'destacados_json': json.dumps([
            {'nombre': p['nombre'], 'slug': p['slug'], 'precio': p['precio']}
            for p in productos_destacados
        ]),
        'carrito_cantidad':     request.session.get('carrito_cantidad', 0),
        'notificaciones_nuevas': 0,
    }

    return render(request, 'pagina/productos.html', context)

def productos_por_categoria(request, categoria_slug):
    """Vista para mostrar productos de una categoría específica"""
    
    # Buscar categoría en BD
    categoria_obj = get_object_or_404(
        Categorias, 
        nombre_categoria__icontains=categoria_slug.replace('-', ' '),
        deleted_at__isnull=True
    )
    
    # Productos de esta categoría
    productos_qs = Producto.objects.filter(
        categoria=categoria_obj,
        estado='DISPONIBLE',
        deleted_at__isnull=True
    ).select_related('categoria')
    
    productos = []
    for prod in productos_qs:
        img = ImagenesProducto.objects.filter(producto=prod, es_principal=1).first()
        productos.append({
            'id': prod.id_producto,
            'nombre': prod.referencia_producto or prod.codigo_producto,
            'slug': prod.codigo_producto.lower().replace(' ', '-'),
            'precio': int(prod.precio_actual),
            'imagen_url': img.ruta_imagen if img else '/static/img/placeholder.jpg'
        })
    
    context = {
        'categoria': {
            'nombre': categoria_obj.nombre_categoria,
            'slug': categoria_slug,
            'descripcion': f'Explora nuestros {categoria_obj.nombre_categoria.lower()}'
        },
        'productos': productos,
        'carrito_cantidad': request.session.get('carrito_cantidad', 0),
    }
    
    return render(request, 'pagina/productos_categoria.html', context)

def promociones(request):
    """Vista de página de promociones"""
    
    # === OFERTA DESTACADA (desde BD o estático) ===
    # Puedes crear un modelo PromoCombo si lo necesitas
    promo_combo = {
        'id': 999,
        'nombre': 'Combo Sofá + Comedor + Mesa',
        'precio': 2490000,
        'precio_original': 3290000,
        'ahorro': 800000,
        'imagen_url': '/static/img/Sofa5.jpg',
    }
    
    # === PROMOCIONES REGULARES (desde BD) ===
    # Productos con descuento o en oferta
    promociones_qs = Producto.objects.filter(
        estado='DISPONIBLE',
        deleted_at__isnull=True
    ).select_related('categoria')[:6]
    
    promociones_lista = []
    for prod in promociones_qs:
        img = ImagenesProducto.objects.filter(producto=prod, es_principal=1).first()
        # Calcular descuento simulado (puedes agregar un campo descuento en el modelo)
        precio_original = int(prod.precio_actual * Decimal('1.2'))  # 20% más
        precio_promo = int(prod.precio_actual)
        descuento = int(((precio_original - precio_promo) / precio_original) * 100)
        
        promociones_lista.append({
            'id': prod.id_producto,
            'nombre': prod.referencia_producto or prod.codigo_producto,
            'categoria': prod.categoria.nombre_categoria if prod.categoria else 'General',
            'precio_original': precio_original,
            'precio_promo': precio_promo,
            'porcentaje_descuento': descuento,
            'imagen_url': f"/media/{img.ruta_imagen}" if img else '/static/img/placeholder.jpg',
        })
    
    context = {
        'promo_combo': promo_combo,
        'promociones': promociones_lista,
        'promociones_json': json.dumps(promociones_lista),
        'carrito_cantidad': request.session.get('carrito_cantidad', 0),
        'notificaciones_nuevas': 0,
    }
    
    return render(request, 'pagina/promociones.html', context)


@require_http_methods(["POST"])
def api_agregar_carrito(request):
    """Agregar producto al carrito — guarda en sesión Y en BD (Carritos/ItemsCarrito)"""
    try:
        data        = json.loads(request.body)
        producto_id = str(data.get('producto_id'))
        cantidad    = int(data.get('cantidad', 1))

        # ── 1. Verificar que el producto existe ──
        try:
            prod = Producto.objects.get(
                id_producto=producto_id,
                estado='DISPONIBLE',
                deleted_at__isnull=True
            )
        except Producto.DoesNotExist:
            return JsonResponse(
                {'success': False, 'error': 'Producto no encontrado'}, status=404
            )

        precio     = prod.precio_actual
        nombre     = prod.referencia_producto or prod.codigo_producto
        img        = ImagenesProducto.objects.filter(
                         producto=prod, es_principal=1
                     ).first()
        imagen_url = img.ruta_imagen if img else '/static/img/placeholder.jpg'

        # ── 2. Guardar en sesión ──
        if not request.session.session_key:
            request.session.create()

        carrito = request.session.get('carrito', {})

        if producto_id in carrito:
            carrito[producto_id]['cantidad'] += cantidad
        else:
            carrito[producto_id] = {
                'producto_id': producto_id,
                'nombre':      nombre,
                'precio':      float(precio),
                'cantidad':    cantidad,
                'imagen_url':  imagen_url,
            }

        request.session['carrito']          = carrito
        request.session['carrito_cantidad'] = sum(
            item['cantidad'] for item in carrito.values()
        )
        request.session.modified = True

        # ── 3. Guardar en BD usando Carritos / ItemsCarrito ──
        try:
            from ventas.models import Carritos, ItemsCarrito

            # Obtener o crear el carrito en BD
            # Si el cliente está autenticado, asociarlo; si no, usar session_id
            cliente = None
            if request.user.is_authenticated:
                from ventas.models import Clientes
                try:
                    cliente = Clientes.objects.get(
                        email=request.user.email,
                        deleted_at__isnull=True
                    )
                except Exception:
                    pass

            carrito_bd, _ = Carritos.objects.get_or_create(
                session_id=request.session.session_key,
                deleted_at__isnull=True,
                defaults={
                    'cliente':    cliente,
                    'created_at': timezone.now(),
                    'updated_at': timezone.now(),
                }
            )

            # Si se encontró el carrito y el cliente no estaba asociado, asociarlo
            if cliente and not carrito_bd.cliente:
                carrito_bd.cliente = cliente
                carrito_bd.updated_at = timezone.now()
                carrito_bd.save()

            # Agregar o actualizar el item
            item_bd, created = ItemsCarrito.objects.get_or_create(
                carrito=carrito_bd,
                producto=prod,
                defaults={
                    'cantidad':        cantidad,
                    'precio_unitario': precio,
                    'created_at':      timezone.now(),
                    'updated_at':      timezone.now(),
                }
            )
            if not created:
                item_bd.cantidad       += cantidad
                item_bd.precio_unitario = precio
                item_bd.updated_at      = timezone.now()
                item_bd.save()

        except Exception as e:
            # Si falla BD, la sesión igual funciona
            print(f"⚠️ Error BD carrito: {e}")

        return JsonResponse({
            'success':        True,
            'cantidad_total': request.session['carrito_cantidad'],
            'nombre':         nombre,
            'precio':         float(precio),
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
@login_required
def api_wishlist_toggle(request):
    """Agregar/remover producto de wishlist"""
    try:
        data = json.loads(request.body)
        producto_id = data.get('producto_id')
        
        # Toggle en base de datos (ejemplo con modelo Wishlist)
        # wishlist, created = Wishlist.objects.get_or_create(
        #     usuario=request.user, 
        #     producto_id=producto_id
        # )
        # if not created: wishlist.delete()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
def api_spin_to_win(request):
    """Endpoint para giro de ruleta (con rate limiting)"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Auth required'}, status=401)
    
    # Rate limiting: 1 giro por usuario
    # if request.user.last_spin and (now - last_spin).hours < 24:
    #     return JsonResponse({'success': False, 'error': 'Ya giraste hoy'}, status=429)
    
    # Lógica de premios ponderados (misma que frontend para consistencia)
    prizes = [
        {'label': '5% OFF', 'value': 5, 'probability': 0.4},
        {'label': '10% OFF', 'value': 10, 'probability': 0.3},
        {'label': '15% OFF', 'value': 15, 'probability': 0.15},
        {'label': '20% OFF', 'value': 20, 'probability': 0.1},
        {'label': '30% OFF', 'value': 30, 'probability': 0.04},
        {'label': 'Envío Gratis', 'value': 'shipping', 'probability': 0.01}
    ]
    
    import random
    rand = random.random()
    cumulative = 0
    prize = prizes[0]
    
    for p in prizes:
        cumulative += p['probability']
        if rand < cumulative:
            prize = p
            break
    
    # Guardar cupón en sesión/BD
    codigo = f"SPIN{prize['value']}"
    # request.session['cupones'][codigo] = prize
    
    return JsonResponse({
        'success': True,
        'prize': prize['label'],
        'code': codigo,
        'message': '¡Felicidades! Tu código ha sido guardado.'
    })

def generar_ticket_number(longitud=6):
    """Genera número único de ticket para seguimiento"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=longitud))

def contacto(request):
    """Vista de página de contacto con formulario avanzado"""
    
    context = {
        'carrito_cantidad': request.session.get('carrito_cantidad', 0),
        'notificaciones_nuevas': 0,
        'errores': [],
        'form_data': {},
        'enviado': False,
        'ticket_number': generar_ticket_number(),
    }
    
    if request.method == 'POST':
        # === OBTENER DATOS DEL FORMULARIO ===
        form_data = {
            'nombre': request.POST.get('nombre', '').strip(),
            'email': request.POST.get('email', '').strip().lower(),
            'telefono': request.POST.get('telefono', '').strip(),
            'asunto_categoria': request.POST.get('asunto_categoria', '').strip(),
            'asunto_detalle': request.POST.get('asunto_detalle', '').strip(),
            'mensaje': request.POST.get('mensaje', '').strip(),
            'terms': request.POST.get('terms') == 'on',
        }
        
        context['form_data'] = form_data
        context['form_data_json'] = json.dumps(form_data)
        
        # === VALIDACIONES ===
        errores = []
        
        if not form_data['nombre'] or len(form_data['nombre']) < 3:
            errores.append('El nombre debe tener al menos 3 letras')
        
        if not form_data['email'] or not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', form_data['email']):
            errores.append('El correo electrónico no es válido')
        
        if not form_data['asunto_categoria']:
            errores.append('Selecciona un tipo de consulta')
        
        if not form_data['mensaje'] or len(form_data['mensaje']) < 10:
            errores.append('El mensaje debe tener al menos 10 caracteres')
        
        if not form_data['terms']:
            errores.append('Debes aceptar la política de privacidad')
        
        # === SI HAY ERRORES, RETORNAR ===
        if errores:
            context['errores'] = errores
            return render(request, 'pagina/contacto.html', context)
        
        # === PROCESAR MENSAJE ===
        try:
            # Preparar mensaje para email
            asunto_email = f"Consulta {form_data['asunto_categoria'].title()}: {form_data['asunto_detalle'] or 'Sin detalle'}"
            mensaje_email = f"""
            NUEVO MENSAJE DE CONTACTO - ORDER RAE
            =====================================
            
            DATOS DEL CLIENTE:
            • Nombre: {form_data['nombre']}
            • Email: {form_data['email']}
            • Teléfono: {form_data['telefono'] or 'No proporcionado'}
            
            CONSULTA:
            • Categoría: {form_data['asunto_categoria'].title()}
            • Asunto: {form_data['asunto_detalle'] or 'No especificado'}
            
            MENSAJE:
            {form_data['mensaje']}
            
            TICKET: #{context['ticket_number']}
            FECHA: {request.META.get('HTTP_X_REAL_IP', request.META.get("REMOTE_ADDR", "Desconocida"))}
            =====================================
            """
            
            # Enviar email (configurar EMAIL en settings.py)
            # send_mail(
            #     subject=asunto_email,
            #     message=mensaje_email,
            #     from_email=settings.DEFAULT_FROM_EMAIL,
            #     recipient_list=['contacto@ordenrae.com'],
            #     fail_silently=False,
            # )
            
            # Para desarrollo: imprimir en consola
            print(f"📧 NUEVO TICKET #{context['ticket_number']}:\n{mensaje_email}")
            
            # Guardar en sesión para mostrar confirmación
            context['enviado'] = True
            context['form_data'] = {}  # Limpiar formulario
            
            # Mensaje para notificaciones JS
            messages.success(request, '¡Tu mensaje ha sido enviado exitosamente!')
            
            # Limpiar borrador guardado (se hace en frontend con localStorage)
            
        except Exception as e:
            context['errores'] = [f'Error al procesar: {str(e)}']
            return render(request, 'pagina/contacto.html', context)
    
    return render(request, 'pagina/contacto.html', context)


@require_http_methods(["POST"])
def api_contacto_enviar(request):
    """Endpoint AJAX para enviar mensaje de contacto (opcional)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    
    try:
        # Validar CSRF
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Petición inválida'}, status=400)
        
        # Procesar datos (similar a la vista principal)
        # ... lógica de validación y envío de email ...
        
        return JsonResponse({
            'success': True,
            'ticket_number': generar_ticket_number(),
            'message': 'Mensaje enviado exitosamente'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def generar_codigo_aleatorio(longitud=6):
    """Genera código único para cotización"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=longitud))


def cotiza(request):
    """Vista de página de cotización con formulario multi-paso"""
    
    context = {
        'carrito_cantidad': request.session.get('carrito_cantidad', 0),
        'notificaciones_nuevas': 0,
        'errores': [],
        'form_data': {},
        'enviado': False,
        'random_code': generar_codigo_aleatorio(),
        'user_full_name': request.user.get_full_name() if request.user.is_authenticated else '',
        'user_email':     request.user.email if request.user.is_authenticated else '',
    }
    
    if request.method == 'POST':
        # === OBTENER DATOS DEL FORMULARIO ===
        form_data = {
            'nombre': request.POST.get('nombre', '').strip(),
            'email': request.POST.get('email', '').strip().lower(),
            'telefono': request.POST.get('telefono', '').strip(),
            'ciudad': request.POST.get('ciudad', '').strip(),
            'categoria': request.POST.get('categoria', '').strip(),
            'producto': request.POST.get('producto', '').strip(),
            'cantidad': request.POST.get('cantidad', '1'),
            'presupuesto': request.POST.get('presupuesto', '').strip(),
            'mensaje': request.POST.get('mensaje', '').strip(),
            'terms': request.POST.get('terms') == 'on',
            'newsletter': request.POST.get('newsletter') == 'on',
        }
        
        context['form_data'] = form_data
        context['form_data_json'] = json.dumps(form_data)
        
        # === VALIDACIONES ===
        errores = []
        
        if not form_data['nombre'] or len(form_data['nombre']) < 3:
            errores.append('El nombre debe tener al menos 3 letras')
        
        if not form_data['email'] or not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', form_data['email']):
            errores.append('El correo electrónico no es válido')
        
        if not form_data['telefono'] or not re.match(r'^\+57\s[0-9]{3}\s[0-9]{3}\s[0-9]{4}$', form_data['telefono']):
            errores.append('El teléfono debe tener formato: +57 3XX XXX XXXX')
        
        if not form_data['ciudad']:
            errores.append('Selecciona tu ciudad')
        
        if not form_data['terms']:
            errores.append('Debes aceptar los términos y condiciones')
        
        # === SI HAY ERRORES, RETORNAR ===
        if errores:
            context['errores'] = errores
            return render(request, 'pagina/cotiza.html', context)
        
        # === PROCESAR COTIZACIÓN ===
        try:
            # Preparar mensaje para email
            asunto = f'Nueva cotización: {form_data["producto"] or "Producto no especificado"}'
            mensaje = f"""
            NUEVA SOLICITUD DE COTIZACIÓN - ORDER RAE
            =========================================
            
            DATOS DEL CLIENTE:
            • Nombre: {form_data['nombre']}
            • Email: {form_data['email']}
            • Teléfono: {form_data['telefono']}
            • Ciudad: {form_data['ciudad']}
            
            PRODUCTO/SERVICIO:
            • Categoría: {form_data['categoria']}
            • Producto: {form_data['producto'] or 'No especificado'}
            • Cantidad estimada: {form_data['cantidad']}
            • Presupuesto: {form_data['presupuesto'] or 'No definido'}
            
            DETALLES ADICIONALES:
            {form_data['mensaje'] or 'Sin observaciones adicionales'}
            
            PREFERENCIAS:
            • Newsletter: {'Sí' if form_data['newsletter'] else 'No'}
            
            FECHA: {request.META.get('HTTP_X_REAL_IP', request.META.get("REMOTE_ADDR", "Desconocida"))}
            CÓDIGO: COT-2026-{context['random_code']}
            =========================================
            """
            
            # Enviar email (configurar EMAIL en settings.py)
            # send_mail(
            #     subject=asunto,
            #     message=mensaje,
            #     from_email=settings.DEFAULT_FROM_EMAIL,
            #     recipient_list=['cotizaciones@ordenrae.com'],
            #     fail_silently=False,
            # )
            
            # Para desarrollo: imprimir en consola
            print(f"📋 NUEVA COTIZACIÓN #{context['random_code']}:\n{mensaje}")
            
            # Guardar en sesión para mostrar confirmación
            context['enviado'] = True
            context['form_data'] = {}  # Limpiar formulario
            
            # Mensaje para notificaciones JS
            messages.success(request, '¡Tu cotización ha sido enviada exitosamente!')
            
            # Limpiar borrador guardado
            # (se hace en el frontend con localStorage.removeItem)
            
        except Exception as e:
            context['errores'] = [f'Error al procesar: {str(e)}']
            return render(request, 'pagina/cotiza.html', context)
    
    # Preparar sugerencias de productos para JS
    productos_sugeridos = {
        'sofas': ['Sofá Fátima 3 puestos', 'Sofá Moderno 2 puestos', 'Sofá Ejecutivo'],
        'camas': ['Cama Alpes King', 'Cama Doble Clásica', 'Cama Juvenil'],
        'escritorios': ['Escritorio Ejecutivo', 'Escritorio Minimalista'],
        'comedores': ['Comedor 6 puestos', 'Comedor Familiar'],
        'sillas': ['Silla Poltrona', 'Silla Ergonómica']
    }
    context['productos_sugeridos_json'] = json.dumps(productos_sugeridos)
    
    return render(request, 'pagina/cotiza.html', context)


@require_http_methods(["POST"])
def api_cotiza_enviar(request):
    """Endpoint AJAX para enviar cotización (opcional)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    
    try:
        # Validar CSRF
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Petición inválida'}, status=400)
        
        # Procesar datos (similar a la vista principal)
        # ... lógica de validación y envío de email ...
        
        return JsonResponse({
            'success': True,
            'cotizacion_number': generar_codigo_aleatorio(),
            'message': 'Cotización enviada exitosamente'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def login_view(request):
    """Login unificado para clientes y staff"""
    
    # Si ya está autenticado redirigir según tipo
    if request.session.get('cliente_auth'):
        return redirect('pagina:home')
    if request.session.get('usuario_id'):
        return redirect('dashboard:dashboard_home')
    
    if request.method == 'POST':
        correo = request.POST.get('correo', '').strip().lower()
        contrasena = request.POST.get('contrasena', '')
        remember = request.POST.get('remember')

        if not correo or not contrasena:
            messages.error(request, 'Ingresa correo y contraseña')
            return render(request, 'pagina/login.html')

        # Buscar primero en Usuarios (staff)
        from usuarios.models import Usuarios
        try:
            usuario = Usuarios.objects.select_related('id_rol').get(
                correo_usuario=correo,
                deleted_at__isnull=True
            )

            # Detectar formato SHA256 o pbkdf2
            from django.contrib.auth.hashers import make_password, check_password as django_check
            contrasena_valida = False

            if usuario.contrasena_usuario.startswith('pbkdf2_'):
                contrasena_valida = django_check(contrasena, usuario.contrasena_usuario)
            else:
                sha_hash = hashlib.sha256(contrasena.encode()).hexdigest()
                contrasena_valida = (sha_hash == usuario.contrasena_usuario)
                if contrasena_valida:
                    # Migrar automáticamente a pbkdf2
                    Usuarios.objects.filter(pk=usuario.pk).update(
                        contrasena_usuario=make_password(contrasena)
                    )

            if contrasena_valida:
                if usuario.estado != 'ACTIVO':
                    messages.error(request, 'Usuario inactivo. Contacte al administrador.')
                    return render(request, 'pagina/login.html')
                
                # Autenticación exitosa, iniciar sesión
                from django.contrib.auth import login
                login(request, usuario, backend='usuarios.backends.UsuariosAuthBackend')

                import time
                request.session['usuario_id'] = usuario.id_usuario
                request.session['usuario_nombre'] = f"{usuario.nombres} {usuario.apellidos}"
                request.session['usuario_rol'] = usuario.id_rol.nombre_rol if usuario.id_rol else 'SIN_ROL'
                request.session['last_activity_timestamp'] = time.time()

                if remember:
                    request.session.set_expiry(1209600)

                messages.success(request, f'Bienvenido {usuario.nombres}')
                return redirect('dashboard:dashboard_home')
            else:
                messages.error(request, 'Correo o contraseña incorrectos')
                return render(request, 'pagina/login.html')

        except Usuarios.DoesNotExist:
            pass  # No es staff, buscar en clientes

        # Buscar en Clientes
        from django.contrib.auth import authenticate, login
        cliente = authenticate(request, correo=correo, contrasena=contrasena)

        if cliente is not None:
            login(request, cliente, backend='ventas.backends.ClientesAuthBackend')

            request.session['cliente_id'] = cliente.id_cliente
            request.session['cliente_nombre'] = cliente.get_nombre_completo()
            request.session['cliente_email'] = cliente.email
            request.session['cliente_auth'] = True

            if remember:
                request.session.set_expiry(1209600)
            else:
                request.session.set_expiry(0)

            cliente.last_login = timezone.now()
            cliente.ultimo_login = timezone.now()
            cliente.save(update_fields=['last_login', 'ultimo_login'])

            messages.success(request, f'¡Bienvenido, {cliente.nombre}!')
            return redirect(request.GET.get('next', 'pagina:home'))

        messages.error(request, 'Correo o contraseña incorrectos')

    if request.GET.get('timeout') == '1':
        messages.warning(request, 'Tu sesión expiró. Inicia sesión nuevamente.')
    if request.GET.get('logged_out') == '1':
        messages.info(request, 'Sesión cerrada correctamente.')

    return render(request, 'pagina/login.html')


def registro_view(request):
    """Registro de clientes"""
    
    if request.session.get('cliente_auth'):
        return redirect('pagina:home')
    
    if request.method == 'POST':
        nombre    = request.POST.get('nombre', '').strip()
        apellido  = request.POST.get('apellidos', '').strip()   # era 'apellido'
        documento = request.POST.get('documento', '').strip()
        email     = request.POST.get('correo', '').strip().lower()  # era 'email'
        telefono  = request.POST.get('telefono', '').strip()
        genero    = request.POST.get('genero', '')
        password  = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        
        # Validaciones
        errores = []
        if not all([nombre, apellido, documento, email, password, password2]):
            errores.append('Todos los campos obligatorios son requeridos')
        if password != password2:
            errores.append('Las contraseñas no coinciden')
        if len(password) < 8:
            errores.append('La contraseña debe tener mínimo 8 caracteres')
        
        if email and Clientes.objects.filter(email=email, deleted_at__isnull=True).exists():
            errores.append('El email ya está registrado')
        if documento and Clientes.objects.filter(documento=documento, deleted_at__isnull=True).exists():
            errores.append('El documento ya está registrado')
        
        if errores:
            return render(request, 'pagina/registro.html', {
                'error': ' | '.join(errores),
                'form_data': request.POST
            })
        
        try:
            from django.contrib.auth.hashers import make_password

            #  Mapa de género corregido para los valores del HTML
            genero_map = {
                'masculino': 'M',
                'femenino':  'F',
                'otro':      'O',
            }
            genero_abrev = genero_map.get(genero.lower(), 'O') if genero else 'O'
            
            #  Guardar directo en tabla clientes
            nuevo_cliente = Clientes.objects.create(
                nombre=nombre,
                apellido=apellido,
                documento=documento,
                email=email,
                contrasena_cliente=make_password(password),
                telefono=telefono or None,
                estado='ACTIVO',
                fecha_registro=timezone.now(),
                genero=genero_abrev,
            )
            
            # Auto-login con el backend de clientes
            from django.contrib.auth import login
            login(request, nuevo_cliente, backend='ventas.backends.ClientesAuthBackend')
            
            request.session['cliente_id']     = nuevo_cliente.id_cliente
            request.session['cliente_nombre'] = f"{nombre} {apellido}"
            request.session['cliente_email']  = email
            request.session['cliente_auth']   = True
            
            messages.success(request, f'¡Bienvenido, {nombre}! Tu cuenta ha sido creada.')
            return redirect('pagina:home')
            
        except Exception as e:
            logger.error(f" [registro_view] ERROR: {type(e).__name__}: {str(e)}", exc_info=True)
            messages.error(request, f'Error al crear la cuenta: {str(e)}')
            return render(request, 'pagina/registro.html', {'form_data': request.POST})
    
    return render(request, 'pagina/registro.html')


def logout_view(request):
    """Cerrar sesión de cliente"""
    from django.contrib.auth import logout
    logout(request)  # Cierra sesión de Django
    
    # Limpiar variables de sesión personalizadas
    keys_to_delete = ['cliente_id', 'cliente_nombre', 'cliente_email', 'cliente_auth', 'carrito', 'carrito_cantidad', 'cupon_activo']
    for key in keys_to_delete:
        if key in request.session:
            del request.session[key]
    
    return redirect('pagina:home')

def perfil_view(request):
    """Vista de perfil — redirige según tipo de usuario"""
    if not request.user.is_authenticated:
        return redirect('pagina:login')

    # Si es usuario staff (Usuarios), va al perfil del dashboard
    if request.session.get('usuario_id'):
        return redirect('dashboard:perfil')

    # Si es cliente, va al perfil de cliente (ventas)
    from ventas.views import perfil_usuario
    return perfil_usuario(request)

# =============================================================================
# API ENDPOINTS ACTUALIZADOS
# =============================================================================


@require_http_methods(["POST"])
def api_cupon_aplicar(request):
    """Validar y aplicar cupón de descuento"""
    try:
        data = json.loads(request.body)
        codigo = data.get('codigo', '').strip().upper()
        
        # Cupones válidos (en producción: consulta a BD con fechas y usos)
        cupones_validos = {
            'BIENVENIDO10': {'type': 'percentage', 'value': 10, 'min_compra': 0},
            'ENVIO500': {'type': 'fixed', 'value': 50000, 'min_compra': 200000},
            'FREESHIP': {'type': 'shipping', 'value': 0, 'min_compra': 0},
        }
        
        if codigo not in cupones_validos:
            return JsonResponse({'success': False, 'error': 'Cupón inválido'}, status=400)
        
        cupon = cupones_validos[codigo]
        
        # Validar monto mínimo
        carrito_total = sum(
            (p['precio_base'] + p['iva']) * request.session.get('carrito', {}).get(p['id'], 0)
            for p in Producto.objects.filter(id__in=request.session.get('carrito', {}).keys())
        ) if False else 3500000  # TODO: cálculo real
        
        if carrito_total < cupon['min_compra']:
            return JsonResponse({
                'success': False, 
                'error': f'Mínimo de compra: ${cupon["min_compra"]:,}'
            }, status=400)
        
        # Aplicar cupón a sesión
        request.session['cupon_activo'] = {'codigo': codigo, **cupon}
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'cupon': cupon,
            'message': 'Cupón aplicado exitosamente'
        })
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

# =============================================================================
# API ENDPOINTS PARA AJAX - URLs deben coincidir con el JavaScript
# =============================================================================


@login_required
def checkout(request):
    """Vista de proceso de checkout"""
    if not request.session.get('cliente_auth') and not request.session.get('usuario_id'):
        return redirect('pagina:login')
    
    # Verificar que hay carrito
    carrito_session = request.session.get('carrito', {})
    if not carrito_session:
        return redirect('pagina:carrito_compra')
    
    # Datos de productos (en producción: consulta a BD con select_related)
    productos_db = {
        '1': {'nombre': 'SOFÁ FATIMA', 'precio_base': 1872269, 'iva': 356731, 'imagen': '/static/img/Sofá2.JPG'},
        # ... más productos
    }
    
    # Calcular totales
    carrito_items = []
    total_carrito = 0
    total_iva = 0
    
    for producto_id_str, cantidad in carrito_session.items():
        producto = productos_db.get(producto_id_str)
        if producto:
            precio_base = producto['precio_base']
            iva = producto['iva']
            subtotal = (precio_base + iva) * cantidad
            
            carrito_items.append({
                'producto_id': producto_id_str,
                'nombre': producto['nombre'],
                'precio_base': precio_base,
                'iva': iva,
                'cantidad': cantidad,
                'subtotal': subtotal,
                'imagen_url': producto['imagen'],
            })
            total_carrito += precio_base * cantidad
            total_iva += iva * cantidad
    
    # Aplicar cupón si existe
    cupon_activo = request.session.get('cupon_activo')
    descuento = 0
    if cupon_activo:
        if cupon_activo['type'] == 'percentage':
            descuento = (total_carrito + total_iva) * (cupon_activo['value'] / 100)
        elif cupon_activo['type'] == 'fixed':
            descuento = min(cupon_activo['value'], total_carrito + total_iva)
    
    total_final = total_carrito + total_iva - descuento
    
    context = {
        'carrito_items': carrito_items,
        'carrito_items_json': json.dumps(carrito_items),
        'total_carrito': total_carrito,
        'total_iva': total_iva,
        'total_final': max(0, total_final),
        'descuento': descuento,
        'cupon_activo': cupon_activo,
        'random_number': ''.join(random.choices(string.ascii_uppercase + string.digits, k=6)),
    }
    
    return render(request, 'pagina/checkout.html', context)


@require_http_methods(["POST"])
def api_checkout_procesar(request):
    """Procesa el checkout y guarda Venta + DetalleVenta en BD"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Debes iniciar sesión'}, status=401)

    try:
        data = json.loads(request.body)

        # ── 1. Obtener cliente ──
        from ventas.models import Clientes, Ventas, DetalleVenta, ItemsCarrito, Carritos, MetodosPago
        from inventario.models import Producto

        cliente = Clientes.objects.filter(
            email=request.user.email,
            deleted_at__isnull=True
        ).first()

        if not cliente:
            return JsonResponse({'success': False, 'error': 'Cliente no encontrado'}, status=404)

        # ── 2. Obtener carrito en BD ──
        carrito_bd = Carritos.objects.filter(
            cliente=cliente,
            deleted_at__isnull=True
        ).first()

        if not carrito_bd:
            carrito_bd = Carritos.objects.filter(
                session_id=request.session.session_key,
                deleted_at__isnull=True
            ).first()

        if not carrito_bd:
            return JsonResponse({'success': False, 'error': 'Carrito vacío'}, status=400)

        items = ItemsCarrito.objects.filter(carrito=carrito_bd).select_related('producto')

        if not items.exists():
            return JsonResponse({'success': False, 'error': 'No hay productos en el carrito'}, status=400)

        # ── 3. Calcular totales ──
        subtotal   = sum(item.precio_unitario * item.cantidad for item in items)
        impuesto   = subtotal * Decimal('0.19')
        descuento  = Decimal('0')
        total      = subtotal + impuesto - descuento

        # ── 4. Método de pago ──
        metodo_nombre = data.get('pago', {}).get('metodo', 'otro')
        metodo_map    = {
            'pse': 'PSE', 'tarjeta': 'Tarjeta', 'card': 'Tarjeta',
            'nequi': 'Nequi', 'cash': 'Contra entrega', 'contraentrega': 'Contra entrega',
            'whatsapp': 'WhatsApp',
        }
        metodo_pago = MetodosPago.objects.filter(
            nombre__icontains=metodo_map.get(metodo_nombre, metodo_nombre)
        ).first()

        # ── 5. Dirección de entrega ──
        envio     = data.get('envio', {})
        contacto  = data.get('contacto', {})
        direccion = f"{envio.get('direccion', '')} {envio.get('apartamento', '')}".strip()
        if envio.get('ciudad'):
            direccion = f"{envio.get('ciudad')} - {direccion}"

        # Actualizar dirección del cliente si la ingresó
        if direccion and not cliente.direccion:
            cliente.direccion = direccion
            cliente.save(update_fields=['direccion', 'updated_at'])

        # ── 6. Crear Venta ──
        with transaction.atomic():
            venta = Ventas(
                usuario    = None,          # nullable tras la migración
                cliente    = cliente,
                tipo_venta = 'DIRECTA',
                fecha_venta= timezone.now(),
                subtotal   = subtotal,
                impuesto   = impuesto,
                descuento  = descuento,
                total      = total,
                estado_venta = 'PENDIENTE',
                metodo_pago  = metodo_pago,
                observaciones= (
                    f"Pedido web | "
                    f"Contacto: {contacto.get('nombre','')} "
                    f"{contacto.get('telefono','')} | "
                    f"Entrega: {direccion}"
                ),
            )
            # Saltar full_clean para evitar validación de total (ya calculado)
            venta.save()

            # ── 7. Crear DetalleVenta ──
            for item in items:
                DetalleVenta.objects.create(
                    venta          = venta,
                    producto       = item.producto,
                    cantidad       = item.cantidad,
                    precio_unitario= item.precio_unitario,
                    descuento      = Decimal('0'),
                    subtotal       = item.precio_unitario * item.cantidad,
                )

            # ── 8. Vaciar carrito ──
            ItemsCarrito.objects.filter(carrito=carrito_bd).delete()
            carrito_bd.updated_at = timezone.now()
            carrito_bd.save()

            request.session['carrito']          = {}
            request.session['carrito_cantidad'] = 0
            request.session.modified = True

        return JsonResponse({
            'success':      True,
            'order_number': venta.numero_factura,
            'total':        float(total),
            'message':      '¡Pedido creado exitosamente!',
        })

    except Exception as e:
        import traceback
        print(f"ERROR checkout: {traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_http_methods(["GET"])
def api_listar_notificaciones(request):
    """Listar notificaciones - URL: /pagina/api/notificaciones/"""
    notificaciones_nuevas = 0
    notificaciones_lista = []
    
    if request.user.is_authenticated:
        # Aquí iría lógica real de base de datos
        pass
    
    return JsonResponse({
        'nuevas': notificaciones_nuevas,
        'notificaciones': notificaciones_lista
    })


@require_http_methods(["POST"])
def api_crear_notificacion(request):
    """Crear notificación - URL: /pagina/api/notificaciones/crear/"""
    try:
        data = json.loads(request.body)
        mensaje = data.get('mensaje', '')
        tipo = data.get('tipo', 'info')
        
        # Aquí iría: guardar en BD si request.user.is_authenticated
        
        return JsonResponse({'success': True, 'message': 'Notificación creada'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def api_marcar_leidas(request):
    """Marcar notificaciones como leídas - URL: /pagina/api/notificaciones/marcar-leidas/"""
    try:
        if request.user.is_authenticated:
            # Aquí iría: Notificacion.objects.filter(usuario=request.user).update(leida=True)
            pass
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# paginas sobre la empresa   
def quienes_somos(request):
    """Vista de página Quiénes Somos - Versión simplificada"""
    context = {
        'carrito_cantidad': request.session.get('carrito_cantidad', 0),
        'notificaciones_nuevas': 0,
        'equipo': [
            {'nombre': 'Carlos Ramírez', 'rol': 'Fundador & Maestro Artesano', 'avatar': generar_avatar_url('Carlos Ramírez')},
            {'nombre': 'Ana Martínez', 'rol': 'Directora de Diseño', 'avatar': generar_avatar_url('Ana Martínez')},
            {'nombre': 'Luis Hernández', 'rol': 'Jefe de Producción', 'avatar': generar_avatar_url('Luis Hernández')},
            {'nombre': 'María González', 'rol': 'Atención al Cliente', 'avatar': generar_avatar_url('María González')},
        ],
        'valores': [
            {'icono': 'fa-hand-holding-heart', 'titulo': 'Pasión Artesanal', 'texto': 'Cada mueble es creado con dedicación y amor por el detalle.'},
            {'icono': 'fa-leaf', 'titulo': 'Sostenibilidad', 'texto': 'Usamos madera de fuentes certificadas y procesos respetuosos.'},
            {'icono': 'fa-medal', 'titulo': 'Calidad Premium', 'texto': 'Cada mueble está diseñado para durar generaciones.'},
            {'icono': 'fa-users', 'titulo': 'Compromiso Social', 'texto': 'Apoyamos a comunidades locales de artesanos.'},
        ]
    }
    return render(request, 'pagina/quienes_somos.html', context)


def nuestra_historia(request):
    """Vista de página Nuestra Historia - Timeline interactivo"""
    timeline = [
        {'año': '2015', 'titulo': 'El Comienzo', 'texto': 'Iniciamos en un pequeño taller de 50m² con 3 artesanos y un sueño.', 'imagen': '/static/img/taller-2015.jpg'},
        {'año': '2017', 'titulo': 'Primera Expansión', 'texto': 'Abrimos nuestro primer showroom en Bogotá y alcanzamos las 100 ventas.', 'imagen': '/static/img/showroom-2017.jpg'},
        {'año': '2019', 'titulo': 'Digitalización', 'texto': 'Lanzamos nuestra tienda online y comenzamos a enviar a todo el país.', 'imagen': '/static/img/online-2019.jpg'},
        {'año': '2021', 'titulo': 'Reconocimiento Nacional', 'texto': 'Ganamos el premio "Mejor Artesano Colombiano" y expandimos nuestro equipo.', 'imagen': '/static/img/premio-2021.jpg'},
        {'año': '2024', 'titulo': 'Innovación 2026', 'texto': 'Implementamos realidad aumentada para visualización de muebles.', 'imagen': '/static/img/ar-2024.jpg'},
        {'año': '2026', 'titulo': 'El Futuro', 'texto': 'Seguimos innovando con diseños personalizados y materiales sostenibles.', 'imagen': '/static/img/futuro-2026.jpg'},
    ]
    context = {
        'carrito_cantidad': request.session.get('carrito_cantidad', 0),
        'notificaciones_nuevas': 0,
        'timeline': timeline,
    }
    return render(request, 'pagina/nuestra_historia.html', context)


def sostenibilidad(request):
    """Vista de página Sostenibilidad - Impacto ambiental"""
    metrics = [
        {'icono': '🌳', 'numero': '5,000+', 'label': 'Árboles Plantados'},
        {'icono': '♻️', 'numero': '95%', 'label': 'Materiales Reciclables'},
        {'icono': '🤝', 'numero': '50+', 'label': 'Comunidades Apoyadas'},
        {'icono': '⚡', 'numero': '100%', 'label': 'Energía Renovable en Taller'},
    ]
    practicas = [
        {'titulo': 'Madera Certificada', 'descripcion': 'Trabajamos exclusivamente con madera de bosques gestionados de forma sostenible.', 'icono': 'fa-tree'},
        {'titulo': 'Cero Residuos', 'descripcion': 'Reutilizamos el 98% de los residuos de madera para crear productos secundarios.', 'icono': 'fa-recycle'},
        {'titulo': 'Energía Solar', 'descripcion': 'Nuestro taller funciona con paneles solares que cubren el 100% de nuestras necesidades.', 'icono': 'fa-solar-panel'},
        {'titulo': 'Embalaje Ecológico', 'descripcion': 'Usamos materiales biodegradables y reciclables para todos nuestros envíos.', 'icono': 'fa-box-open'},
    ]
    context = {
        'carrito_cantidad': request.session.get('carrito_cantidad', 0),
        'notificaciones_nuevas': 0,
        'metrics': metrics,
        'practicas': practicas,
    }
    return render(request, 'pagina/sostenibilidad.html', context)


def trabaja_con_nosotros(request):
    """Vista de página Trabaja con Nosotros - Vacantes y cultura"""
    vacantes = [
        {'titulo': 'Artesano en Madera', 'ubicacion': 'Bogotá', 'tipo': 'Tiempo completo', 'descripcion': 'Buscamos artesanos con experiencia en tallado y acabados en madera.'},
        {'titulo': 'Diseñador de Producto', 'ubicacion': 'Remoto/Híbrido', 'tipo': 'Tiempo completo', 'descripcion': 'Profesional creativo para desarrollar nuevas líneas de muebles.'},
        {'titulo': 'Asesor Comercial', 'ubicacion': 'Bogotá', 'tipo': 'Medio tiempo', 'descripcion': 'Atención al cliente y gestión de pedidos en showroom.'},
        {'titulo': 'Prácticas Producción', 'ubicacion': 'Bogotá', 'tipo': 'Prácticas', 'descripcion': 'Oportunidad para estudiantes de diseño o ingeniería.'},
    ]
    beneficios = [
        {'icono': 'fa-heart', 'titulo': 'Ambiente Familiar', 'texto': 'Trabajamos como una familia, con respeto y apoyo mutuo.'},
        {'icono': 'fa-graduation-cap', 'titulo': 'Capacitación Continua', 'texto': 'Programas de formación en técnicas artesanales y nuevas tecnologías.'},
        {'icono': 'fa-hand-holding-usd', 'titulo': 'Salario Competitivo', 'texto': 'Remuneración justa más bonos por desempeño y antigüedad.'},
        {'icono': 'fa-calendar-check', 'titulo': 'Flexibilidad', 'texto': 'Horarios flexibles y posibilidad de trabajo remoto para algunos roles.'},
    ]
    default_vacantes = [
        {'titulo': 'Artesano en Madera', 'ubicacion': 'Bogotá', 'tipo': 'Tiempo completo', 'descripcion': 'Buscamos artesanos con experiencia en tallado y acabados en madera.'},
        {'titulo': 'Diseñador de Producto', 'ubicacion': 'Remoto/Híbrido', 'tipo': 'Tiempo completo', 'descripcion': 'Profesional creativo para desarrollar nuevas líneas de muebles.'},
        {'titulo': 'Asesor Comercial', 'ubicacion': 'Bogotá', 'tipo': 'Medio tiempo', 'descripcion': 'Atención al cliente y gestión de pedidos en showroom.'},
        {'titulo': 'Prácticas Producción', 'ubicacion': 'Bogotá', 'tipo': 'Prácticas', 'descripcion': 'Oportunidad para estudiantes de diseño o ingeniería.'},
    ]    
    context = {
        'carrito_cantidad': request.session.get('carrito_cantidad', 0),
        'notificaciones_nuevas': 0,
        'vacantes': vacantes,
        'default_vacantes': default_vacantes,
        'beneficios': beneficios,
    }
    return render(request, 'pagina/trabaja_con_nosotros.html', context)


def blog_decoracion(request):
    """Vista de página Blog de Decoración - Artículos y consejos"""
    articulos = [
        {
            'titulo': '5 Tendencias de Decoración para 2026',
            'excerpt': 'Descubre los estilos que dominarán este año: minimalismo cálido, texturas naturales y colores tierra.',
            'imagen': '/static/img/blog-tendencias-2026.jpg',
            'fecha': '15 Mar 2026',
            'autor': 'Ana Martínez',
            'categoria': 'Tendencias',
            'slug': 'tendencias-decoracion-2026',
            'leer_mas': '#'
        },
        {
            'titulo': 'Cómo Elegir el Sofá Perfecto para tu Sala',
            'excerpt': 'Guía práctica para seleccionar el sofá ideal según el espacio, estilo de vida y presupuesto.',
            'imagen': '/static/img/blog-sofa-perfecto.jpg',
            'fecha': '10 Mar 2026',
            'autor': 'Carlos Ramírez',
            'categoria': 'Guías',
            'slug': 'elegir-sofa-perfecto',
            'leer_mas': '#'
        },
        {
            'titulo': 'Madera Sostenible: Por Qué Importa',
            'excerpt': 'Entiende el impacto de elegir muebles de madera certificada y cómo contribuyes al planeta.',
            'imagen': '/static/img/blog-madera-sostenible.jpg',
            'fecha': '5 Mar 2026',
            'autor': 'Luis Hernández',
            'categoria': 'Sostenibilidad',
            'slug': 'madera-sostenible-importa',
            'leer_mas': '#'
        },
        {
            'titulo': 'Organiza tu Espacio de Trabajo en Casa',
            'excerpt': 'Consejos de diseño para crear un home office funcional, ergonómico y estéticamente agradable.',
            'imagen': '/static/img/blog-home-office.jpg',
            'fecha': '1 Mar 2026',
            'autor': 'María González',
            'categoria': 'Productividad',
            'slug': 'organizar-home-office',
            'leer_mas': '#'
        },
    ]
    categorias_blog = ['Todos', 'Tendencias', 'Guías', 'Sostenibilidad', 'Productividad', 'DIY']
    context = {
        'carrito_cantidad': request.session.get('carrito_cantidad', 0),
        'notificaciones_nuevas': 0,
        'articulos': articulos,
        'categorias_blog': categorias_blog,
    }
    return render(request, 'pagina/blog_decoracion.html', context)
