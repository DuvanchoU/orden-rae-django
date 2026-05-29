from django.shortcuts import render, redirect, get_object_or_404, Http404
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
from ventas.models import Carritos, ItemsCarrito
from django.contrib.auth import logout
from django.contrib.auth import authenticate, login, logout

# Vistas para páginas principales (home, productos, promociones, contacto, etc.)
# Vistas para autenticación (login, registro, perfil)
# Vistas para manejo de carrito y checkout
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
@csrf_protect
def actualizar_avatar(request):
    """
    Endpoint AJAX para actualizar avatar desde base64 o URL estática.
    Compatible con el modelo Clientes.
    """
    import base64, re, uuid, os, json
    from django.core.files.base import ContentFile
    from django.conf import settings
    from ventas.models import Clientes
    
    try:
        # 1. Parsear JSON
        data = json.loads(request.body)
        avatar_data = data.get('avatar_url', '')
        
        if not avatar_data:
            return JsonResponse({'success': False, 'error': 'No se recibió la imagen'}, status=400)
        
        # 2. Obtener cliente
        cliente = Clientes.objects.filter(
            email=request.user.email,
            deleted_at__isnull=True
        ).first()
        
        if not cliente:
            return JsonResponse({'success': False, 'error': 'Cliente no encontrado'}, status=404)
        
        # 3. CASO: URL estática (default-avatar)
        if 'default-avatar' in avatar_data or avatar_data.startswith('/static/'):
            cliente.foto_perfil = avatar_data.replace('/static/', 'static/')
            cliente.save(update_fields=['foto_perfil'])
            return JsonResponse({
                'success': True,
                'foto_url': cliente.foto_perfil.url if hasattr(cliente.foto_perfil, 'url') else avatar_data,
                'mensaje': 'Avatar actualizado'
            })
        
        # 4. CASO: Base64 (data:image/png;base64,... o image/png;base64,...)
        if 'base64' in avatar_data:
            # ← Regex que acepta "data:" opcional
            match = re.match(r'(?:data:)?image/(\w+);base64,(.+)', avatar_data, re.DOTALL)
            if not match:
                print(f"❌ Regex no coincide. Avatar data: {avatar_data[:50]}...")
                return JsonResponse({'success': False, 'error': 'Formato de imagen inválido'}, status=400)
            
            ext = match.group(1)  # png, jpg, jpeg, webp
            img_data = match.group(2)  # el base64 puro
            
            try:
                image_file = ContentFile(base64.b64decode(img_data))
                filename = f'avatar_cliente_{cliente.id_cliente}_{uuid.uuid4().hex[:8]}.{ext}'
                
                upload_path = os.path.join(settings.MEDIA_ROOT, 'avatars')
                os.makedirs(upload_path, exist_ok=True)
                
                file_path = os.path.join(upload_path, filename)
                with open(file_path, 'wb+') as f:
                    for chunk in image_file.chunks():
                        f.write(chunk)
                
                cliente.foto_perfil = f'avatars/{filename}'
                cliente.save(update_fields=['foto_perfil'])
                
                return JsonResponse({
                    'success': True,
                    'foto_url': cliente.foto_perfil.url,
                    'mensaje': 'Foto actualizada correctamente'
                })
                
            except Exception as decode_error:
                print(f"❌ Error decodificando base64: {decode_error}")
                return JsonResponse({'success': False, 'error': f'Error al procesar imagen: {str(decode_error)}'}, status=500)
        
        return JsonResponse({'success': False, 'error': 'Formato no soportado'}, status=400)
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Datos JSON inválidos'}, status=400)
    except Exception as e:
        print(f"❌ Error general avatar: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f'Error del servidor: {str(e)}'}, status=500)

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
        'productos':               page_obj,     
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
        return redirect('home')
    if request.session.get('usuario_id'):
        return redirect('dashboard:dashboard_home') 
    
    if request.method == 'POST':
        correo = request.POST.get('correo', '').strip().lower()
        contrasena = request.POST.get('contrasena', '')
        remember = request.POST.get('remember')

        if not correo or not contrasena:
            messages.error(request, 'Ingresa correo y contraseña')
            return render(request, 'pagina/login.html')


        # ========================================
        # 1. Buscar primero en Usuarios (staff)
        # ========================================
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
        # ========================================
        # 2. Buscar en Clientes (TIENDA WEB)
        # ========================================
        from ventas.models import Clientes
        from django.contrib.auth.hashers import check_password as django_check

        try:
            cliente = Clientes.objects.get(
                email=correo,
                deleted_at__isnull=True
            )

            # Verificar contraseña
            contrasena_valida = False

            # Contraseña Django
            if (
                cliente.contrasena_cliente and
                cliente.contrasena_cliente.startswith('pbkdf2_')
            ):
                contrasena_valida = django_check(
                    contrasena,
                    cliente.contrasena_cliente
                )

            # Contraseña SHA256 antigua
            else:
                sha_hash = hashlib.sha256(contrasena.encode()).hexdigest()
                contrasena_valida = (
                    sha_hash == cliente.contrasena_cliente
                )

            # Validar contraseña y estado
            if (
                contrasena_valida and
                cliente.estado == 'ACTIVO'
            ):

                # Login cliente
                request.session['cliente_auth'] = True
                request.session['cliente_id'] = cliente.id_cliente
                request.session['cliente_nombre'] = cliente.nombre_cliente

                return redirect('/')

            else:
                messages.error(
                    request,
                    'Correo o contraseña incorrectos'
                )

        except Clientes.DoesNotExist:
            logger.debug(f'Cliente no existe: {correo}')
            login(request, cliente, backend='ventas.backends.ClientesAuthBackend')

            request.session['cliente_id'] = cliente.id_cliente
            request.session['cliente_nombre'] = f"{cliente.nombre} {cliente.apellido}"
            request.session['cliente_email'] = cliente.email
            request.session['cliente_auth'] = True

            if remember:
                request.session.set_expiry(1209600)
            else:
                request.session.set_expiry(0)

            cliente.ultimo_login = timezone.now()
            cliente.save(update_fields=['ultimo_login'])

            messages.success(request, f'¡Bienvenido, {cliente.nombre}!')

            # Redirigir a la página anterior o al home
            return redirect(request.GET.get('next', '/'))

        except Clientes.DoesNotExist:
            # No existe ni en Usuarios ni en Clientes
            messages.error(request, 'Correo o contraseña incorrectos')
            return render(request, 'pagina/login.html')


    # ========================================
    # GET: Mostrar formulario de login
    # ========================================
    if request.GET.get('timeout') == '1':
        messages.warning(request, 'Tu sesión expiró. Inicia sesión nuevamente.')
    if request.GET.get('logged_out') == '1':
        messages.info(request, 'Sesión cerrada correctamente.')

    return render(request, 'pagina/login.html')


def registro_view(request):
    """Vista de registro de clientes - SIN verificación de email"""
    
    # Si ya está autenticado, redirigir
    if request.session.get('cliente_id') or hasattr(request.user, 'id_usuario'):
        return redirect('pagina:home')
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        apellido = request.POST.get('apellidos', '').strip()
        documento = request.POST.get('documento', '').strip()
        email = request.POST.get('correo', '').strip().lower()
        telefono = request.POST.get('telefono', '').strip()
        genero = request.POST.get('genero', '')
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        
        errores = []
# Validaciones básicas
        if not all([nombre, apellido, documento, email, password, password2]):
            errores.append('Todos los campos obligatorios son requeridos')

        # Validar formato de email
        if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            errores.append('El correo electrónico no es válido')

        # Validar contraseñas
        if password != password2:
            errores.append('Las contraseñas no coinciden')

        if password and len(password) < 8:
            errores.append('La contraseña debe tener mínimo 8 caracteres')

        # Validar documento
        if documento and len(documento) < 5:
            errores.append('El documento debe tener al menos 5 dígitos')

        # Verificar duplicados
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
            # Convertir género
            genero_abreviado = None
            if genero:
                if genero.lower() in ['masculino', 'm', 'hombre']:
                    genero_abreviado = 'M'
                elif genero.lower() in ['femenino', 'f', 'mujer']:
                    genero_abreviado = 'F'
                else:
                    genero_abreviado = 'O'
            
            # Hash con SHA256
            import hashlib
            contrasena_hash = hashlib.sha256(password.encode()).hexdigest()
            
            # Crear cliente CON email_verificado=True (sin necesidad de confirmar)
            nuevo_cliente = Clientes.objects.create(
                nombre=nombre,
                apellido=apellido,
                documento=documento,
                email=email,
                contrasena_cliente=contrasena_hash,
                telefono=telefono if telefono else None,
                estado='ACTIVO',
                fecha_registro=timezone.now(),
                genero=genero_abreviado,
                created_at=timezone.now(),
                email_verificado=True,
                )

            # Auto-login con backend de clientes
            from django.contrib.auth import login

            login(
                request,
                nuevo_cliente,
                backend='ventas.backends.ClientesAuthBackend'
            )

            request.session['cliente_id'] = nuevo_cliente.id_cliente
            request.session['cliente_nombre'] = f"{nombre} {apellido}"
            request.session['cliente_email'] = email
            request.session['cliente_auth'] = True

            messages.success(
                request,
                f'¡Bienvenido, {nombre}! Tu cuenta ha sido creada.'
            )
            return redirect('pagina:login')
            
        except IntegrityError as e:
            print(f"❌ ERROR de integridad: {e}")
            messages.error(request, 'Ocurrió un error. Intenta nuevamente.')
        except Exception as e:
            print(f"❌ ERROR: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'Error: {str(e)}')
        
        return render(request, 'pagina/registro.html', {
            'form_data': request.POST
        })
    
    return render(request, 'pagina/registro.html')

def logout_view(request):
    """Cerrar sesión de cliente"""
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
        data   = json.loads(request.body)
        codigo = data.get('codigo', '').strip().upper()

        cupones_validos = {
            'BIENVENIDO10': {'tipo': 'porcentaje', 'valor': 10,    'min_compra': 0},
            'ENVIO500':     {'tipo': 'fijo',       'valor': 50000, 'min_compra': 200000},
            'FREESHIP':     {'tipo': 'porcentaje', 'valor': 0,     'min_compra': 0},
            'ORDERRAE20':   {'tipo': 'porcentaje', 'valor': 20,    'min_compra': 0},
        }

        if codigo not in cupones_validos:
            return JsonResponse(
                {'success': False, 'error': 'Cupón inválido o expirado'}, status=400
            )

        cupon = cupones_validos[codigo]

        # ── Calcular total del carrito ──────────────────────────────────────
        from ventas.models import Carritos, ItemsCarrito

        carrito_bd    = None
        total_con_iva = Decimal('0')

        # Buscar carrito en BD (cliente autenticado primero, luego sesión)
        if request.user.is_authenticated:
            from ventas.models import Clientes as C
            cliente = C.objects.filter(
                email=request.user.email, deleted_at__isnull=True
            ).first()
            if cliente:
                carrito_bd = Carritos.objects.filter(
                    cliente=cliente, deleted_at__isnull=True
                ).first()

        if not carrito_bd and request.session.session_key:
            carrito_bd = Carritos.objects.filter(
                session_id=request.session.session_key, deleted_at__isnull=True
            ).first()

        if carrito_bd:
            items = ItemsCarrito.objects.filter(
                carrito=carrito_bd
            ).select_related('producto')
            for item in items:
                precio        = Decimal(str(item.precio_unitario))
                subtotal      = precio * item.cantidad
                total_con_iva += subtotal + (subtotal * Decimal('0.19'))
        else:
            # Fallback: sesión de Django
            carrito_session = request.session.get('carrito', {})
            for pid, item_data in carrito_session.items():
                if not isinstance(item_data, dict):
                    continue
                precio        = Decimal(str(item_data.get('precio', 0)))
                cantidad      = int(item_data.get('cantidad', 1))
                subtotal      = precio * cantidad
                total_con_iva += subtotal + (subtotal * Decimal('0.19'))

        total_con_iva = total_con_iva.quantize(Decimal('0.01'))

        if total_con_iva <= 0:
            return JsonResponse(
                {'success': False, 'error': 'Tu carrito está vacío'}, status=400
            )

        # ── Validar monto mínimo ────────────────────────────────────────────
        if total_con_iva < Decimal(str(cupon['min_compra'])):
            return JsonResponse({
                'success': False,
                'error':   f'Monto mínimo para este cupón: ${cupon["min_compra"]:,.0f}'
            }, status=400)

        # ── Calcular descuento ──────────────────────────────────────────────
        if cupon['tipo'] == 'porcentaje':
            descuento = (
                total_con_iva * Decimal(str(cupon['valor'])) / 100
            ).quantize(Decimal('0.01'))
        elif cupon['tipo'] == 'fijo':
            descuento = min(Decimal(str(cupon['valor'])), total_con_iva)
        else:
            descuento = Decimal('0')

        total_final = max(Decimal('0'), total_con_iva - descuento)

        # ── Guardar en sesión — claves UNIFICADAS (una sola convención) ─────
        request.session['cupon_activo'] = {
            'codigo':    codigo,
            'tipo':      cupon['tipo'],   # 'porcentaje' | 'fijo'
            'valor':     cupon['valor'],
            'descuento': float(descuento),
        }
        request.session.modified = True

        return JsonResponse({
            'success':     True,
            'codigo':      codigo,
            'tipo':        cupon['tipo'],
            'valor':       cupon['valor'],
            'descuento':   float(descuento),
            'total_final': float(total_final),
            'mensaje':     f'Cupón aplicado: −${descuento:,.0f}',
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
@require_http_methods(["POST"])
def api_cupon_remover(request):
    """Remover cupón activo de la sesión"""
    request.session.pop('cupon_activo', None)
    request.session.modified = True
    return JsonResponse({'success': True})

# =============================================================================
# API ENDPOINTS PARA AJAX - URLs deben coincidir con el JavaScript
# =============================================================================


@login_required
def checkout(request):
    """Vista de proceso de checkout — requiere sesión de cliente autenticado"""
    if not request.session.get('cliente_auth') and not request.session.get('usuario_id'):
        return redirect('pagina:login')
 
    carrito_session = request.session.get('carrito', {})
    if not carrito_session:
        messages.warning(request, 'Tu carrito está vacío. Agrega productos antes de continuar.')
        return redirect('pagina:productos')
 
    carrito_items = []
    total_carrito = 0
    total_iva     = 0
 
    # Consultar productos en bloque (eficiente)
    producto_ids = list(carrito_session.keys())
    productos_qs = Producto.objects.filter(
        id_producto__in=producto_ids,
        estado='DISPONIBLE',
        deleted_at__isnull=True
    ).select_related('categoria')
    productos_map = {str(p.id_producto): p for p in productos_qs}
 
    for producto_id_str, item_data in carrito_session.items():
        if isinstance(item_data, dict):
            cantidad    = int(item_data.get('cantidad', 1))
            precio_base = float(item_data.get('precio', item_data.get('precio_base', 0)))
            nombre      = item_data.get('nombre', 'Producto')
            imagen_url  = item_data.get('imagen_url', '/static/img/placeholder.jpg')
            sku         = item_data.get('sku', producto_id_str)
        else:
            cantidad    = int(item_data)
            precio_base = 0
            nombre      = 'Producto'
            imagen_url  = '/static/img/placeholder.jpg'
            sku         = producto_id_str
 
        prod = productos_map.get(producto_id_str)
        if prod:
            precio_base = float(prod.precio_actual)
            nombre      = prod.referencia_producto or prod.codigo_producto
            sku         = prod.codigo_producto
            img         = ImagenesProducto.objects.filter(producto=prod, es_principal=1).first()
            if img:
                imagen_url = img.ruta_imagen
 
        iva_unitario        = round(precio_base * 0.19, 2)
        iva_total           = round(iva_unitario * cantidad, 2)
        subtotal            = round(precio_base * cantidad, 2)
        subtotal_con_iva    = round(subtotal + iva_total, 2)
 
        carrito_items.append({
            'item_id':          producto_id_str,
            'producto_id':      producto_id_str,
            'nombre':           nombre,
            'sku':              sku,
            'precio_base':      precio_base,
            'iva':              iva_unitario,
            'iva_total':        iva_total,
            'subtotal_con_iva': subtotal_con_iva,
            'cantidad':         cantidad,
            'subtotal':         subtotal,
            'imagen_url':       imagen_url,
            'stock':            99,
        })
 
        total_carrito += subtotal
        total_iva     += iva_total
 
    # Cupón
    cupon_activo  = request.session.get('cupon_activo')
    descuento     = 0
    total_con_iva = round(total_carrito + total_iva, 2)

    if cupon_activo:
        tipo  = cupon_activo.get('tipo', '')      
        valor = cupon_activo.get('valor', 0)        
        if tipo == 'porcentaje':
            descuento = round(total_con_iva * valor / 100, 2)
        elif tipo == 'fijo':
            descuento = min(valor, total_con_iva)

    total_final = max(0, round(total_con_iva - descuento, 2))
 
    carrito_items_json = json.dumps([
        {**item, 'precio_base': item['precio_base'], 'iva': item['iva']}
        for item in carrito_items
    ], ensure_ascii=False)
 
    context = {
        'carrito_items':      carrito_items,
        'carrito_items_json': carrito_items_json,
        'carrito_cantidad':   sum(i['cantidad'] for i in carrito_items),
        'total_carrito':      round(total_carrito, 2),
        'total_iva':          round(total_iva, 2),
        'total_final':        total_final,
        'descuento':          round(descuento, 2),
        'descuento_aplicado': descuento > 0,
        'cupon_activo':       cupon_activo,
        'hay_items':          len(carrito_items) > 0,
        'random_number':      ''.join(random.choices(string.ascii_uppercase + string.digits, k=6)),
        'STRIPE_PUBLIC_KEY': getattr(settings, 'STRIPE_PUBLIC_KEY', '')
    }
 
    return render(request, 'pagina/checkout.html', context)
 
@require_http_methods(["POST"])
def api_checkout_procesar(request):
    """
    Procesa el checkout completo:
    1. Crea Pedido + DetallePedido (en tabla pedido / detalle_pedido)
    2. Crea Venta + DetalleVenta  (en tabla ventas / detalle_venta)
    3. Limpia el carrito (BD + sesión)
    4. Genera número de factura y número de pedido
    5. Retorna JSON con número de orden y totales
    """
    import traceback
    from decimal import Decimal, ROUND_HALF_UP
    from django.db import transaction
    from django.utils import timezone
 
    # ── Auth ──────────────────────────────────────────────────────────────────
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Debes iniciar sesión para continuar.'}, status=401)
 
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Datos enviados no válidos.'}, status=400)
 
    try:
        from ventas.models import (
            Clientes, Ventas, DetalleVenta,
            ItemsCarrito, Carritos, MetodosPago,
            Pedido, DetallePedido,
        )
        from inventario.models import Producto
        from usuarios.models import Usuarios
 
        # ── 1. Obtener cliente ───────────────────────────────────────────────
        cliente = None
        if isinstance(request.user, Clientes):
            cliente = request.user
        else:
            cliente = Clientes.objects.filter(
                email=request.user.email,
                deleted_at__isnull=True
            ).first()
 
        if not cliente:
            return JsonResponse(
                {'success': False, 'error': 'No se encontró el cliente. Inicia sesión nuevamente.'},
                status=404
            )
 
        # ── 2. Recopilar items del carrito (BD primero, sesión como fallback) ──
        items_data = []
 
        carrito_bd = (
            Carritos.objects.filter(cliente=cliente, deleted_at__isnull=True).first()
            or Carritos.objects.filter(
                session_id=request.session.session_key,
                deleted_at__isnull=True
            ).first()
        )
 
        if carrito_bd:
            for item in ItemsCarrito.objects.filter(carrito=carrito_bd).select_related('producto'):
                if item.producto and item.cantidad > 0:
                    items_data.append({
                        'producto':        item.producto,
                        'cantidad':        item.cantidad,
                        'precio_unitario': Decimal(str(item.precio_unitario)),
                    })
 
        # Fallback: sesión de Django
        if not items_data:
            carrito_session = request.session.get('carrito', {})
            if not carrito_session:
                return JsonResponse(
                    {'success': False, 'error': 'Tu carrito está vacío. Agrega productos antes de continuar.'},
                    status=400
                )
            productos_map = {
                str(p.id_producto): p
                for p in Producto.objects.filter(
                    id_producto__in=list(carrito_session.keys()),
                    estado='DISPONIBLE',
                    deleted_at__isnull=True
                )
            }
            for prod_id_str, item_data_s in carrito_session.items():
                prod = productos_map.get(prod_id_str)
                if not prod:
                    continue
                cantidad = int(item_data_s.get('cantidad', 1)) if isinstance(item_data_s, dict) else int(item_data_s)
                items_data.append({
                    'producto':        prod,
                    'cantidad':        cantidad,
                    'precio_unitario': Decimal(str(prod.precio_actual)),
                })
 
        if not items_data:
            return JsonResponse(
                {'success': False, 'error': 'No hay productos válidos en el carrito.'},
                status=400
            )
 
        # ── 3. Calcular totales ──────────────────────────────────────────────
        # Q garantiza exactamente 2 decimales en cada paso.
        # Sin esto, la suma final puede tener precisión interna extra
        # que Django DecimalField(decimal_places=2) rechaza con ValidationError.
        Q = Decimal('0.01')
 
        subtotal = sum(
            (item['precio_unitario'] * item['cantidad']).quantize(Q, rounding=ROUND_HALF_UP)
            for item in items_data
        ).quantize(Q, rounding=ROUND_HALF_UP)
 
        impuesto  = (subtotal * Decimal('0.19')).quantize(Q, rounding=ROUND_HALF_UP)
        descuento = Decimal('0.00')
 
        cupon = request.session.get('cupon_activo')
        if cupon:
            tipo  = cupon.get('tipo', '')
            valor = Decimal(str(cupon.get('valor', 0)))
            total_con_iva = (subtotal + impuesto).quantize(Q, rounding=ROUND_HALF_UP)
            if tipo == 'porcentaje':
                descuento = (
                    total_con_iva * valor / 100
                ).quantize(Q, rounding=ROUND_HALF_UP)
            elif tipo == 'fijo':
                descuento = min(valor, total_con_iva).quantize(Q, rounding=ROUND_HALF_UP)
 
        # FIX: cuantizar el total final — la suma de Decimals puede generar
        # precision interna extra que Django rechaza en DecimalField(decimal_places=2)
        total = (subtotal + impuesto - descuento).quantize(Q, rounding=ROUND_HALF_UP)
 
        # ── 4. Método de pago ────────────────────────────────────────────────
        metodo_raw = data.get('pago', {}).get('metodo', '')
        metodo_map = {
            'pse':           'PSE',
            'card':          'Tarjeta',
            'tarjeta':       'Tarjeta',
            'nequi':         'Nequi',
            'cash':          'Contra entrega',
            'contraentrega': 'Contra entrega',
            'whatsapp':      'WhatsApp',
        }
        nombre_metodo = metodo_map.get(metodo_raw, metodo_raw)
        metodo_pago = None
        if nombre_metodo:
            metodo_pago = MetodosPago.objects.filter(
                nombre__icontains=nombre_metodo,
                deleted_at__isnull=True
            ).first()
            if not metodo_pago:
                metodo_pago, _ = MetodosPago.objects.get_or_create(
                    nombre=nombre_metodo,
                    defaults={
                        'descripcion': f'Método de pago: {nombre_metodo}',
                        'created_at':  timezone.now(),
                        'updated_at':  timezone.now(),
                    }
                )
 
        # ── 5. Datos de envío y contacto ─────────────────────────────────────
        envio    = data.get('envio', {})
        contacto = data.get('contacto', {})
 
        partes_direccion = [
            envio.get('ciudad', ''),
            envio.get('direccion', ''),
            envio.get('apartamento', ''),
        ]
        direccion_envio = ' - '.join(p.strip() for p in partes_direccion if p.strip())
 
        instrucciones = envio.get('instrucciones', '').strip()
        observaciones = (
            f"Pedido web | "
            f"Contacto: {contacto.get('nombre', '')} {contacto.get('telefono', '')} | "
            f"Entrega: {direccion_envio}"
        )
        if instrucciones:
            observaciones += f" | Instrucciones: {instrucciones}"
 
        ahora         = timezone.now()
        fecha_entrega = (ahora + timezone.timedelta(days=5)).date()
 
        # ── 6. Guardar todo en transacción atómica ───────────────────────────
        with transaction.atomic():
 
            # FIX: usuario_id es NOT NULL en pedido y ventas.
            # Usamos el usuario sistema (id=1). Cámbialo por el id de tu admin si prefieres.
            usuario_sistema = Usuarios.objects.filter(pk=1).first()
 
            # ── 6a. Generar número de pedido único ───────────────────────────
            ultimo_pedido = Pedido.objects.filter(
                deleted_at__isnull=True
            ).order_by('-id_pedido').first()
            consec_pedido = (ultimo_pedido.id_pedido if ultimo_pedido else 0) + 1
            numero_pedido = f"PED-{consec_pedido:06d}"
 
            while Pedido.objects.filter(numero_pedido=numero_pedido).exists():
                consec_pedido += 1
                numero_pedido = f"PED-{consec_pedido:06d}"
 
            # FIX 1: Reemplazado Pedido.__new__()/__init__() por constructor normal.
            # FIX 2: estado_pedido='CONFIRMADO' no existe en el ENUM de la BD.
            #         Valores válidos: 'PENDIENTE', 'EN PROCESO', 'ENTREGADO', 'CANCELADO'
            # FIX 3: usuario=None rompe la FK NOT NULL → usar usuario_sistema.
            pedido = Pedido(
                cliente=cliente,
                usuario=usuario_sistema,
                asesor=None,
                fecha_pedido=ahora,
                fecha_entrega_estimada=fecha_entrega,
                total_pedido=total,
                estado_pedido='PENDIENTE',        # ← único valor correcto para pedidos nuevos
                estado_facturacion='NO_FACTURADO',
                direccion_entrega=direccion_envio,
                numero_pedido=numero_pedido,
                created_at=ahora,
                updated_at=ahora,
            )
            pedido.save()
 
            # ── 6c. Crear DetallePedido ──────────────────────────────────────
            for item in items_data:
                subtotal_item = (
                    item['precio_unitario'] * item['cantidad']
                ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
 
                DetallePedido(
                    pedido=pedido,
                    producto=item['producto'],
                    cantidad=item['cantidad'],
                    precio_unitario=item['precio_unitario'],
                    subtotal=subtotal_item,
                    created_at=ahora,
                    updated_at=ahora,
                ).save()
 
            # ── 6d. Generar número de factura único ──────────────────────────
            prefijo      = 'FAC'
            ultimo_venta = Ventas.objects.filter(
                prefijo=prefijo,
                deleted_at__isnull=True
            ).order_by('-id_venta').first()
            consec_venta   = (ultimo_venta.id_venta if ultimo_venta else 0) + 1
            numero_factura = f"{prefijo}-{consec_venta:06d}"
 
            while Ventas.objects.filter(numero_factura=numero_factura).exists():
                consec_venta += 1
                numero_factura = f"{prefijo}-{consec_venta:06d}"
 
            # FIX 1: Reemplazado Ventas.__new__()/__init__() por constructor normal.
            # FIX 2: usuario=None rompe FK NOT NULL → usar usuario_sistema.
            # FIX 3: estado_venta ENUM válidos: 'COMPLETADA', 'CANCELADA', 'PENDIENTE'
            venta = Ventas(
                usuario=usuario_sistema,
                cliente=cliente,
                pedido=pedido,
                tipo_venta='DIRECTA',
                fecha_venta=ahora,
                subtotal=subtotal,
                impuesto=impuesto,
                descuento=descuento,
                total=total,
                estado_venta='PENDIENTE',          # ← valor válido en el ENUM
                metodo_pago=metodo_pago,
                observaciones=observaciones,
                numero_factura=numero_factura,
                prefijo=prefijo,
                created_at=ahora,
                updated_at=ahora,
            )
            venta.save()
 
            # ── 6f. Crear DetalleVenta ───────────────────────────────────────
            detalles_venta = []
            for item in items_data:
                subtotal_item = (
                    item['precio_unitario'] * item['cantidad']
                ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
 
                detalle = DetalleVenta(
                    venta=venta,
                    producto=item['producto'],
                    cantidad=item['cantidad'],
                    precio_unitario=item['precio_unitario'],
                    descuento=Decimal('0.00'),
                    subtotal=subtotal_item,
                    costo_estimado=None,
                    created_at=ahora,
                    updated_at=ahora,
                )
                detalle.save()
                detalles_venta.append(detalle)
 
            # ── 6g. Actualizar dirección del cliente si no tenía ─────────────
            # FIX: usar getattr() para evitar AttributeError si el campo no existe
            if direccion_envio and not getattr(cliente, 'direccion', None):
                Clientes.objects.filter(pk=cliente.pk).update(
                    direccion=direccion_envio,
                    updated_at=ahora
                )
 
            # ── 6h. Marcar timestamp de actualización en pedido ──────────────
            Pedido.objects.filter(pk=pedido.pk).update(updated_at=ahora)
 
            # ── 6i. Vaciar carrito en BD ─────────────────────────────────────
            if carrito_bd:
                ItemsCarrito.objects.filter(carrito=carrito_bd).delete()
                Carritos.objects.filter(pk=carrito_bd.pk).update(
                    deleted_at=ahora,
                    updated_at=ahora
                )
 
            # ── 6j. Vaciar carrito en sesión ─────────────────────────────────
            request.session['carrito']          = {}
            request.session['carrito_cantidad'] = 0
            request.session.pop('cupon_activo', None)
            request.session.modified = True
 
        # ── 7. URL de factura PDF ─────────────────────────────────────────────
        factura_url = f"/ventas/factura/{venta.id_venta}/pdf/"
 
        # ── 8. Respuesta exitosa ──────────────────────────────────────────────
        return JsonResponse({
            'success':       True,
            'order_number':  venta.numero_factura,
            'pedido_number': pedido.numero_pedido,
            'total':         float(total),
            'subtotal':      float(subtotal),
            'impuesto':      float(impuesto),
            'descuento':     float(descuento),
            'items':         len(detalles_venta),
            'metodo_pago':   nombre_metodo,
            'factura_url':   factura_url,
            'message':       '¡Pedido creado exitosamente! Recibirás la confirmación en tu correo.',
        })
 
    except Exception as e:
        print(f"[CHECKOUT ERROR]\n{traceback.format_exc()}")
        return JsonResponse(
            {'success': False, 'error': f'Error al procesar la compra: {str(e)}'},
            status=500
        )

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

def pqrs(request):
    """Vista de página PQRS - Formulario de contacto"""
    context = {
        'carrito_cantidad': request.session.get('carrito_cantidad', 0),
        'notificaciones_nuevas': 0,
    }
    return render(request, 'pagina/pqrs.html', context)

def rastrear_pedido(request):
    """Vista de página Rastrear Pedido - Seguimiento en tiempo real"""
    context = {
        'carrito_cantidad': request.session.get('carrito_cantidad', 0),
        'notificaciones_nuevas': 0,
    }
    return render(request, 'pagina/rastrear_pedido.html', context)


def info_ayuda(request, slug):
    """
    Vista para páginas de ayuda.
    slug: 'materiales', 'cuidado', 'envios', 'devoluciones', 'preguntas_frecuentes'
    """
    #  Slugs válidos → valor exacto que espera la plantilla
    PAGINAS_VALIDAS = {
        'materiales': 'materiales',
        'cuidado': 'cuidado', 
        'envios': 'envios',
        'devoluciones': 'devoluciones',
        'preguntas_frecuentes': 'preguntas_frecuentes',  
    }
    
    # Validar slug
    if slug not in PAGINAS_VALIDAS:
        raise Http404("Página de ayuda no encontrada")
    
    # Títulos para SEO
    TITULOS = {
        'materiales': 'Guía de Materiales',
        'cuidado': 'Cuidado de Muebles',
        'envios': 'Política de Envíos',
        'devoluciones': 'Devoluciones y Garantía',
        'preguntas_frecuentes': 'Preguntas Frecuentes',
    }
    
    context = {
        'pagina': PAGINAS_VALIDAS[slug],     
        'titulo_seccion': TITULOS[slug],
        'slug_actual': slug,
    }
    
    return render(request, 'partials/info_ayuda.html', context)

# Vistas para Email y recuperación de contraseña 

import hashlib
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.conf import settings
from ventas.models import Clientes
from ventas.utils import (
    generar_token_seguro,
    enviar_email_verificacion,
    enviar_email_reset_password,
    validar_token_verificacion,
    validar_token_reset_password
)


def enviar_verificacion_email_view(request):
    """Reenviar email de verificación"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        
        try:
            cliente = Clientes.objects.get(
                email=email, 
                email_verificado=False,
                deleted_at__isnull=True
            )
            
            if enviar_email_verificacion(cliente):
                messages.success(request, f'Hemos enviado un nuevo email de verificación a {email}')
            else:
                messages.error(request, 'Error al enviar el email. Intenta nuevamente.')
                
        except Clientes.DoesNotExist:
            messages.error(request, 'No encontramos una cuenta pendiente de verificación con ese email.')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return redirect('pagina:login')


def verificar_email_view(request, token):
    """Validar token y activar cuenta del cliente"""
    
    cliente = validar_token_verificacion(token)
    
    if cliente:
        # Activar cuenta
        cliente.email_verificado = True
        cliente.token_verificacion = None
        cliente.token_verificacion_expira = None
        cliente.save(update_fields=['email_verificado', 'token_verificacion', 'token_verificacion_expira'])
        
        messages.success(request, f'✅ ¡Email verificado! Ahora puedes iniciar sesión, {cliente.nombre}.')
        return redirect('pagina:login')
    else:
        # Token inválido o expirado
        messages.error(request, '❌ El enlace de verificación ha expirado o no es válido. Solicita uno nuevo.')
        return redirect('pagina:login')

def recuperar_password_view(request):
    """Vista para solicitar recuperación de contraseña (PÚBLICA)"""
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        
        if not email:
            messages.error(request, 'Por favor ingresa tu correo electrónico')
            return render(request, 'pagina/recuperar_password.html')
        
        try:
            cliente = Clientes.objects.get(
                email=email,
                email_verificado=True,
                estado='ACTIVO',
                deleted_at__isnull=True
            )
            
            if enviar_email_reset_password(cliente):
                messages.success(request, f'Hemos enviado instrucciones de recuperación a {email}')
            else:
                messages.error(request, 'Error al enviar el email.')
                
        except Clientes.DoesNotExist:
            # No revelar si el email existe (seguridad)
            messages.success(request, f'Si existe una cuenta con {email}, recibirás instrucciones.')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        
        return redirect('pagina:login')
    
    return render(request, 'pagina/recuperar_password.html')


def reset_password_confirm_view(request, token):
    """Vista para establecer nueva contraseña con token válido (PÚBLICA)"""
    
    cliente = validar_token_reset_password(token)
    
    if not cliente:
        messages.error(request, 'El enlace de recuperación ha expirado o no es válido.')
        return redirect('pagina:recuperar_password')
    
    if request.method == 'POST':
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        
        errores = []
        
        if len(password) < 8:
            errores.append('La contraseña debe tener al menos 8 caracteres')
        
        if password != password2:
            errores.append('Las contraseñas no coinciden')
        
        if errores:
            for error in errores:
                messages.error(request, error)
            return render(request, 'pagina/reset_password_confirm.html', {'token': token})
        
        try:
            # Actualizar contraseña con SHA256
            cliente.contrasena_cliente = hashlib.sha256(password.encode()).hexdigest()
            
            # Invalidar token
            cliente.token_reset_password = None
            cliente.token_reset_password_expira = None
            cliente.last_login = timezone.now()
            cliente.ultimo_login = timezone.now()
            
            cliente.save(update_fields=[
                'contrasena_cliente', 
                'token_reset_password', 
                'token_reset_password_expira',
                'last_login',
                'ultimo_login'
            ])
            
            messages.success(request, ' ¡Contraseña actualizada exitosamente!')
            return redirect('pagina:login')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'pagina/reset_password_confirm.html', {'token': token, 'cliente': cliente})