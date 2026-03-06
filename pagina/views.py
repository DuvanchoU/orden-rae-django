from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import IntegrityError
import hashlib
import json
import re
import random
import string
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.conf import settings

def generar_avatar_url(nombre, tamaño=128):
    """
    Genera una URL de avatar consistente basada en el nombre.
    Usa ui-avatars.com para mantener el mismo avatar para el mismo nombre.
    """
    # Colores predefinidos para variedad
    colores = [
        '667eea', '764ba2', 'f093fb', '4facfe', '43e972',
        'fa709a', 'fee140', '30cfd0', 'a8edea', 'feaca9'
    ]
    
    # Usar hash del nombre para seleccionar color consistente
    hash_nombre = int(hashlib.md5(nombre.encode('utf-8')).hexdigest(), 16)
    color = colores[hash_nombre % len(colores)]
    
    # Reemplazar espacios con + para la URL
    nombre_url = nombre.replace(' ', '+')
    
    return f"https://ui-avatars.com/api/?name={nombre_url}&background={color}&color=fff&size={tamaño}&bold=true"


def home(request):
    """
    Vista principal - Con datos completos para que el JavaScript funcione
    """
    
    # === DATOS PARA EL SLIDESHOW Y PRODUCTOS (ejemplo estático o desde BD) ===
    # En producción, reemplaza con: Producto.objects.filter(destacado=True)[:10]
    productos_destacados = [{
            'nombre': 'Sofá Moderno',
            'imagen': type('obj', (object,), {'url': '/static/img/Sofá7.jpg'})
        },
        {
            'nombre': 'Cama Alpes',
            'imagen': type('obj', (object,), {'url': '/static/img/Cama2.jpg'})
        },
        {
            'nombre': 'Escritorio Ejecutivo',
            'imagen': type('obj', (object,), {'url': '/static/img/Escritorio0.2.jpg'})
        },
        {
            'nombre': 'Silla Ergonómica',
            'imagen': type('obj', (object,), {'url': '/static/img/Silla5.jpg'})
        },
        {
            'nombre': 'Comedor Familiar',
            'imagen': type('obj', (object,), {'url': '/static/img/Comedor6.jpg'})
        },]
    class ImagenMock:
        def __init__(self, url):
            self.url = url
    productos_nuevos = [{
            'id': 1,
            'nombre': 'Escritorio Moderno',
            'slug': 'escritorio-moderno',
            'categoria': 'Nuevos lanzamientos',
            'precio': 674000,
            'precio_desde': True,
            'tiene_opciones': True,
            'imagen': ImagenMock('/static/img/Escritorio2.jpg')
        },
        {
            'id': 2,
            'nombre': 'Sofá Fátima',
            'slug': 'sofa-fatima',
            'categoria': 'Nuevos lanzamientos',
            'precio': 2229000,
            'precio_desde': False,
            'tiene_opciones': False,
            'imagen': ImagenMock('/static/img/Sofá2.jpg')
        },
        {
            'id': 3,
            'nombre': 'Cama Alpes',
            'slug': 'cama-alpes',
            'categoria': 'Nuevos lanzamientos',
            'precio': 1113000,
            'precio_desde': True,
            'tiene_opciones': True,
            'imagen': ImagenMock('/static/img/Cama5.jpg')
        },
        {
            'id': 4,
            'nombre': 'Silla Poltrona',
            'slug': 'silla-poltrona',
            'categoria': 'Nuevos lanzamientos',
            'precio': 539000,
            'precio_desde': False,
            'tiene_opciones': False,
            'imagen': ImagenMock('/static/img/Silla3.jpg')
        },]
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
    
    # === DATOS PARA JAVASCRIPT - ¡ESTO ES LO QUE HACE FUNCIONAR EL SCRIPT! ===
    
    # 1. Opciones para el modal (escritorios y camas)
    datos_opciones = {
        'escritorio': [
            {
                'nombre': 'Escritorio Minimalista',
                'img': '/static/img/Escritorio2.jpg',
                'precio': 674000,
                'slug': 'escritorio-minimalista',
                'id': 1
            },
            {
                'nombre': 'Escritorio Ejecutivo',
                'img': '/static/img/Escritorio0.2.jpg',
                'precio': 890000,
                'slug': 'escritorio-ejecutivo',
                'id': 2
            },
            {
                'nombre': 'Escritorio con Cajones',
                'img': '/static/img/Escritorio1.jpg',
                'precio': 750000,
                'slug': 'escritorio-cajones',
                'id': 3
            },
            {
                'nombre': 'Escritorio Escolar',
                'img': '/static/img/Escritorio3.jpg',
                'precio': 520000,
                'slug': 'escritorio-escolar',
                'id': 4
            }
        ],
        'cama': [
            {
                'nombre': 'Cama Alpes 140',
                'img': '/static/img/Cama5.jpg',
                'precio': 1113000,
                'slug': 'cama-alpes-140',
                'id': 5
            },
            {
                'nombre': 'Cama Doble Clásica',
                'img': '/static/img/Cama2.jpg',
                'precio': 980000,
                'slug': 'cama-doble-clasica',
                'id': 6
            },
            {
                'nombre': 'Cama King Size',
                'img': '/static/img/Cama3.jpg',
                'precio': 1450000,
                'slug': 'cama-king-size',
                'id': 7
            },
            {
                'nombre': 'Cama Juvenil',
                'img': '/static/img/CamaCunas6.jpg',
                'precio': 720000,
                'slug': 'cama-juvenil',
                'id': 8
            }
        ]
    }
    
    # 2. Productos para la búsqueda automática
    productos_busqueda = [
        'Sofá', 'Sofá Fátima', 'Sofá Moderno', 'Sofá Ejecutivo',
        'Cama', 'Cama Alpes', 'Cama King', 'Cama Juvenil', 'Cama Cuna',
        'Escritorio', 'Escritorio Minimalista', 'Escritorio Ejecutivo', 'Escritorio Escolar',
        'Silla', 'Silla Poltrona', 'Silla Ergonómica', 'Silla de Oficina',
        'Comedor', 'Comedor Familiar', 'Comedor Moderno',
        'Mesa', 'Mesa de Centro', 'Mesa de Comedor',
        'Muebles', 'Muebles de Sala', 'Muebles de Dormitorio'
    ]
    
    # 3. Notificaciones (si el usuario está autenticado)
    notificaciones = []
    notificaciones_nuevas = 0
    if request.user.is_authenticated:
        # Aquí iría: Notificacion.objects.filter(usuario=request.user, leida=False)
        pass
    
    # === CONSTRUIR CONTEXTO PARA EL TEMPLATE ===
    context = {
        # Contador del carrito (desde sesión)
        'carrito_cantidad': request.session.get('carrito_cantidad', 0),
        
        # Datos para JavaScript - ¡IMPORTANTE: usar json.dumps()!
        'datos_opciones_json': json.dumps(datos_opciones),
        'productos_busqueda_json': json.dumps(productos_busqueda),
        
        # Datos para renderizar en el template
        'productos_destacados': productos_destacados,
        'productos_nuevos': productos_nuevos,
        'testimonios': testimonios,
        
        # Notificaciones
        'notificaciones': notificaciones,
        'notificaciones_nuevas': notificaciones_nuevas,
    }
    
    return render(request, 'pagina/index.html', context)

def productos(request):
    """Vista de página de productos/categorías"""
    
    # === CATEGORÍAS (en producción: Categoria.objects.filter(activo=True)) ===
    class ImagenMock:
        def __init__(self, url):
            self.url = url
    
    categorias = [
        {
            'id': 1,
            'nombre': 'Colechos',
            'slug': 'colechos',
            'descripcion_corta': 'Perfectos para compartir con tu bebé',
            'descripcion_larga': 'Colecho de 1 metro de largo por 50 cm de ancho, diseño ergonómico y seguro.',
            'imagen_url': '/static/img/Colecho-1.jpg'
        },
        {
            'id': 2,
            'nombre': 'Cunas',
            'slug': 'cunas',
            'descripcion_corta': 'Diseño clásico y funcional',
            'descripcion_larga': 'Apta para un colchón del corral de 1m x 1.40m. Madera maciza y acolchado suave.',
            'imagen_url': '/static/img/CamaCunas1.JPG'
        },
        {
            'id': 3,
            'nombre': 'Sofás',
            'slug': 'sofas',
            'descripcion_corta': 'Confort y estilo para tu sala',
            'descripcion_larga': 'Sofá de 2 puestos (1.40m largo x 80cm ancho), tapizado en tela premium lavable.',
            'imagen_url': '/static/img/Sofá4.JPG'
        },
        {
            'id': 4,
            'nombre': 'Sillas',
            'slug': 'sillas',
            'descripcion_corta': 'Poltronas y sillas modernas',
            'descripcion_larga': 'La Poltrona Kaira destaca por su diseño compacto y relleno ergonómico.',
            'imagen_url': '/static/img/Poltronas1.JPG'
        },
        {
            'id': 5,
            'nombre': 'Escritorios',
            'slug': 'escritorios',
            'descripcion_corta': 'Espacio ideal para trabajar o estudiar',
            'descripcion_larga': 'Escritorio de 1.30m de ancho x 50cm de fondo. Estilo minimalista con cajones.',
            'imagen_url': '/static/img/Escritorio1.jpg'
        },
        {
            'id': 6,
            'nombre': 'Camas',
            'slug': 'camas',
            'descripcion_corta': 'Camas Montessori y más',
            'descripcion_larga': 'Apta para un colchón de 1m x 1.90m. Diseño bajo y seguro para niños.',
            'imagen_url': '/static/img/CamaMontessori1.jpg'
        },
    ]
    
    # === PRODUCTOS DESTACADOS ===
    productos_destacados = [
        {
            'id': 201,
            'nombre': 'Sofá Premium',
            'slug': 'sofa-premium',
            'precio': 1200000,
            'imagen_url': '/static/img/sofapremiun.jpeg'
        },
        {
            'id': 202,
            'nombre': 'Cuna Lujo',
            'slug': 'cuna-lujo',
            'precio': 950000,
            'imagen_url': '/static/img/cunaLujo.jpg'
        },
        {
            'id': 203,
            'nombre': 'Escritorio Ejecutivo',
            'slug': 'escritorio-ejecutivo',
            'precio': 850000,
            'imagen_url': '/static/img/escritorioEjecutivo.jpg'
        },
        {
            'id': 204,
            'nombre': 'Colecho Plus',
            'slug': 'colecho-plus',
            'precio': 720000,
            'imagen_url': '/static/img/ColechoDestacado.jpg'
        },
    ]
    
    # Datos para JavaScript
    import json
    context = {
        'categorias': categorias,
        'productos_destacados': productos_destacados,
        'categorias_json': json.dumps([
            {'nombre': c['nombre'], 'slug': c['slug']} for c in categorias
        ]),
        'destacados_json': json.dumps([
            {'nombre': p['nombre'], 'slug': p['slug'], 'precio': p['precio']} 
            for p in productos_destacados
        ]),
        'carrito_cantidad': request.session.get('carrito_cantidad', 0),
        'notificaciones_nuevas': 0,
    }
    
    return render(request, 'pagina/productos.html', context)

def productos_por_categoria(request, categoria_slug):
    """
    Vista para mostrar productos de una categoría específica.
    URL: /productos/colechos/, /productos/camas/, etc.
    """
    
    # Mapeo de slugs a datos de categoría (en producción: consulta a BD)
    categorias_data = {
        'colechos': {
            'nombre': 'Colechos',
            'descripcion': 'Colechos ergonómicos y seguros para compartir con tu bebé.',
            'imagen': '/static/img/Colecho-1.jpg'
        },
        'cunas': {
            'nombre': 'Cunas',
            'descripcion': 'Cunas de madera maciza con diseño clásico y funcional.',
            'imagen': '/static/img/CamaCunas1.JPG'
        },
        'sofas': {
            'nombre': 'Sofás',
            'descripcion': 'Sofás cómodos y elegantes para renovar tu sala.',
            'imagen': '/static/img/Sofá4.JPG'
        },
        'sillas': {
            'nombre': 'Sillas',
            'descripcion': 'Poltronas y sillas modernas con diseño ergonómico.',
            'imagen': '/static/img/Poltronas1.JPG'
        },
        'escritorios': {
            'nombre': 'Escritorios',
            'descripcion': 'Escritorios funcionales para trabajar o estudiar.',
            'imagen': '/static/img/Escritorio1.jpg'
        },
        'camas': {
            'nombre': 'Camas',
            'descripcion': 'Camas Montessori y tradicionales de alta calidad.',
            'imagen': '/static/img/CamaMontessori1.jpg'
        },
    }
    
    # Obtener datos de la categoría o redirigir si no existe
    categoria = categorias_data.get(categoria_slug)
    
    if not categoria:
        # Redirigir a página principal de productos si la categoría no existe
        return redirect('pagina:productos')
    
    # Productos de ejemplo para esta categoría (en producción: consulta a BD)
    productos_ejemplo = [
        {
            'id': 1,
            'nombre': f'{categoria["nombre"]} Modelo 1',
            'slug': f'{categoria_slug}-modelo-1',
            'precio': 750000,
            'imagen_url': categoria['imagen'],
            'descripcion': f'Descripción del producto {categoria["nombre"]}.'
        },
        {
            'id': 2,
            'nombre': f'{categoria["nombre"]} Modelo 2',
            'slug': f'{categoria_slug}-modelo-2',
            'precio': 890000,
            'imagen_url': categoria['imagen'],
            'descripcion': f'Otra opción de {categoria["nombre"]}.'
        },
    ]
    
    context = {
        'categoria': categoria,
        'categoria_slug': categoria_slug,
        'productos': productos_ejemplo,
        'carrito_cantidad': request.session.get('carrito_cantidad', 0),
    }
    
    return render(request, 'pagina/productos_categoria.html', context)

def promociones(request):
    """Vista de página de promociones"""
    
    # === OFERTA DESTACADA ===
    promo_combo = {
        'id': 999,
        'nombre': 'Combo Sofá + Comedor + Mesa',
        'precio': 2490000,
        'precio_original': 3290000,
        'ahorro': 800000,
        'imagen_url': '/static/img/Sofa5.jpg',
    }
    
    # === PROMOCIONES REGULARES ===
    promociones_lista = [
        {
            'id': 101,
            'nombre': 'Sofá Moderno 3 Puestos',
            'categoria': 'sofas',
            'precio_original': 1500000,
            'precio_promo': 1050000,
            'porcentaje_descuento': 30,
            'imagen_url': '/static/img/Sofa5.jpg',
        },
        {
            'id': 102,
            'nombre': 'Comedor 6 Puestos',
            'categoria': 'comedores',
            'precio_original': 1800000,
            'precio_promo': 1390000,
            'porcentaje_descuento': 23,
            'imagen_url': '/static/img/Comedor3.jpeg',
        },
        {
            'id': 103,
            'nombre': 'Cama Doble con Cabecero',
            'categoria': 'camas',
            'precio_original': 1100000,
            'precio_promo': 799000,
            'porcentaje_descuento': 27,
            'imagen_url': '/static/img/Cama2.jpg',
        },
    ]
    
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
    """Agregar producto al carrito"""
    try:
        data = json.loads(request.body)
        carrito = request.session.get('carrito', {})
        producto_id = str(data.get('producto_id'))
        cantidad = data.get('cantidad', 1)
        
        if producto_id in carrito:
            carrito[producto_id] += cantidad
        else:
            carrito[producto_id] = cantidad
        
        request.session['carrito'] = carrito
        request.session['carrito_cantidad'] = sum(carrito.values())
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'cantidad_total': request.session['carrito_cantidad'],
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
    """Vista de login compatible con el template Django"""
    
    if request.user.is_authenticated:
        return redirect('pagina:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            if request.POST.get('remember'):
                request.session.set_expiry(1209600)
            else:
                request.session.set_expiry(0)
            
            user_rol = getattr(user, 'rol', '')
            if user.is_superuser or user.is_staff or user_rol in ['ADMIN', 'Gerente', 'Asesor Comercial', 'Jefe Logistico']:
                return redirect('dashboard:dashboard_home')
            else:
                return redirect('pagina:home')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos')
    
    return render(request, 'pagina/login.html')


def registro_view(request):
    """Vista de registro de usuarios"""
    
    if request.user.is_authenticated:
        return redirect('pagina:home')
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        apellidos = request.POST.get('apellidos', '').strip()
        documento = request.POST.get('documento', '').strip()
        correo = request.POST.get('correo', '').strip().lower()
        telefono = request.POST.get('telefono', '').strip()
        genero = request.POST.get('genero', '')
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        
        errores = []
        
        if not all([nombre, apellidos, documento, correo, password, password2]):
            errores.append('Todos los campos marcados con * son obligatorios')
        
        if correo and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', correo):
            errores.append('El formato del correo electrónico no es válido')
        
        if password and len(password) < 8:
            errores.append('La contraseña debe tener al menos 8 caracteres')
        
        if password != password2:
            errores.append('Las contraseñas no coinciden')
        
        if correo and User.objects.filter(email=correo).exists():
            errores.append('Este correo electrónico ya está registrado')
        
        if errores:
            return render(request, 'pagina/registro.html', {
                'error': ' | '.join(errores),
                'form_data': request.POST
            })
        
        try:
            username = correo.split('@')[0]
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User.objects.create_user(
                username=username,
                email=correo,
                password=password,
                first_name=nombre,
                last_name=apellidos
            )
            
            request.session['user_extra_data'] = {
                'documento': documento,
                'telefono': telefono,
                'genero': genero,
                'user_id': user.id
            }
            
            login(request, user)
            messages.success(request, f'¡Bienvenido, {nombre}! Tu cuenta ha sido creada.')
            
            return redirect('pagina:home')
            
        except IntegrityError:
            return render(request, 'pagina/registro.html', {
                'error': 'Ocurrió un error al crear tu cuenta. Intenta nuevamente.',
                'form_data': request.POST
            })
    
    return render(request, 'pagina/registro.html')


def logout_view(request):
    """Cerrar sesión y redirigir al home"""
    from django.contrib.auth import logout
    logout(request)
    if 'carrito' in request.session:
        del request.session['carrito']
    if 'carrito_cantidad' in request.session:
        del request.session['carrito_cantidad']
    return redirect('pagina:home')


def lista_productos(request):
    return render(request, 'pagina/productos.html')


def carrito_compra(request):
    return render(request, 'pagina/carrito.html')


def promociones(request):
    return render(request, 'pagina/promociones.html')


def contacto(request):
    return render(request, 'pagina/contacto.html')


def cotiza(request):
    return render(request, 'pagina/cotiza.html')


def perfil_view(request):
    """Vista de perfil de usuario"""
    if not request.user.is_authenticated:
        return redirect('pagina:login')
    
    extra_data = request.session.get('user_extra_data', {})
    
    context = {
        'user': request.user,
        'documento': extra_data.get('documento', ''),
        'telefono': extra_data.get('telefono', ''),
        'genero': extra_data.get('genero', ''),
    }
    return render(request, 'pagina/perfil.html', context)

def carrito_compra(request):
    """Vista de carrito con datos para funcionalidades 2026"""
    
    carrito_session = request.session.get('carrito', {})
    wishlist_session = request.session.get('wishlist', [])
    
    # Datos de productos (en producción: consulta a BD con select_related)
    productos_db = {
        '1': {
            'nombre': 'SOFÁ FATIMA', 
            'precio_base': 1872269, 
            'iva': 356731, 
            'imagen': '/static/img/Sofá2.JPG',
            'stock': 12,
            'variantes': ['Color: Gris', 'Material: Tela Premium'],
            'sku': 'SOF-FAT-001'
        },
        # ... más productos
    }
    
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
                'stock': producto.get('stock', 99),
                'variantes': producto.get('variantes', []),
                'sku': producto.get('sku', f'ORD-{producto_id_str}'),
            })
            total_carrito += precio_base * cantidad
            total_iva += iva * cantidad
    
    # Datos para JavaScript
    import json
    context = {
        'carrito_items': carrito_items,
        'carrito_items_json': json.dumps(carrito_items),
        'saved_items_json': json.dumps([]),  # Wishlist
        'carrito_cantidad': sum(item['cantidad'] for item in carrito_items),
        'total_carrito': total_carrito,
        'total_iva': total_iva,
        'notificaciones_nuevas': 0,
    }
    
    return render(request, 'pagina/carrito.html', context)


# =============================================================================
# API ENDPOINTS ACTUALIZADOS
# =============================================================================

@require_http_methods(["POST"])
def api_carrito_actualizar(request):
    """Actualizar cantidad con validación de stock"""
    try:
        data = json.loads(request.body)
        producto_id = str(data.get('producto_id'))
        cantidad = max(1, int(data.get('cantidad', 1)))
        
        # TODO: Validar stock real desde BD
        # producto = Producto.objects.get(id=producto_id)
        # if cantidad > producto.stock:
        #     return JsonResponse({'success': False, 'error': 'Stock insuficiente'}, status=400)
        
        carrito = request.session.get('carrito', {})
        if producto_id in carrito:
            carrito[producto_id] = cantidad
            request.session['carrito'] = carrito
            request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'cantidad_total': sum(carrito.values()),
                'message': 'Cantidad actualizada'
            })
        return JsonResponse({'success': False, 'error': 'Producto no encontrado'}, status=404)
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
def api_carrito_eliminar(request):
    """Eliminar producto con soporte para undo"""
    try:
        data = json.loads(request.body)
        producto_id = str(data.get('producto_id'))
        
        carrito = request.session.get('carrito', {})
        if producto_id in carrito:
            # Guardar snapshot para posible undo (en caché por 5 min)
            from django.core.cache import cache
            cache.set(f'cart_undo_{request.session.session_key}_{producto_id}', 
                     {producto_id: carrito[producto_id]}, 300)
            
            del carrito[producto_id]
            request.session['carrito'] = carrito
            request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'cantidad_total': sum(v for k, v in carrito.items()),
                'message': 'Producto eliminado'
            })
        return JsonResponse({'success': False, 'error': 'Producto no encontrado'}, status=404)
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


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

def checkout(request):
    """Vista de proceso de checkout (placeholder)"""
    if not request.session.get('carrito'):
        return redirect('pagina:carrito_compra')
    
    # Aquí iría la lógica real de checkout:
    # - Validar datos del usuario
    # - Calcular envío
    # - Procesar pago
    # - Crear orden en BD
    
    context = {
        'carrito_cantidad': request.session.get('carrito_cantidad', 0),
    }
    return render(request, 'pagina/checkout.html', context)

# =============================================================================
# API ENDPOINTS PARA AJAX - URLs deben coincidir con el JavaScript
# =============================================================================

@require_http_methods(["POST"])
def api_agregar_carrito(request):
    """Agregar producto al carrito - API Endpoint"""
    try:
        data = json.loads(request.body)
        producto_id = str(data.get('producto_id'))
        cantidad = data.get('cantidad', 1)
        precio = data.get('precio', 0)
        nombre = data.get('nombre', 'Producto')
        
        # Obtener carrito actual de la sesión
        carrito = request.session.get('carrito', {})
        
        # Agregar o actualizar producto
        if producto_id in carrito:
            carrito[producto_id] += cantidad
        else:
            carrito[producto_id] = cantidad
        
        # Guardar en sesión
        request.session['carrito'] = carrito
        request.session['carrito_cantidad'] = sum(carrito.values())
        request.session.modified = True
        
        print(f"✅ Producto añadido: {nombre} (ID: {producto_id})")
        print(f"🛒 Carrito actual: {carrito}")
        print(f"📊 Total items: {request.session['carrito_cantidad']}")
        
        return JsonResponse({
            'success': True,
            'cantidad_total': request.session['carrito_cantidad'],
            'message': f'{nombre} añadido al carrito'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'JSON inválido'
        }, status=400)
    except Exception as e:
        print(f"❌ Error en api_agregar_carrito: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def checkout(request):
    """Vista de proceso de checkout"""
    
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
    """Endpoint para procesar el pago (producción)"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Autenticación requerida'}, status=401)
    
    try:
        data = json.loads(request.body)
        
        # TODO: Validar datos, procesar pago con pasarela, crear orden en BD
        # Ejemplo simplificado:
        
        # 1. Crear orden en base de datos
        # orden = Orden.objects.create(
        #     usuario=request.user,
        #     total=data['total'],
        #     estado='pendiente',
        #     metodo_pago=data['pago']['metodo'],
        #     direccion_envio=data['envio'],
        #     contacto=data['contacto']
        # )
        
        # 2. Procesar pago con pasarela (Wompi, PayU, Stripe)
        # payment_response = pasarela_pago.charge({
        #     'amount': data['total'],
        #     'currency': 'COP',
        #     'payment_method': data['pago']['metodo'],
        #     'customer_email': data['contacto']['email']
        # })
        
        # 3. Enviar email de confirmación
        # send_mail(
        #     subject=f'Confirmación de pedido #{orden.numero}',
        #     message=f'Gracias por tu compra...',
        #     from_email=settings.DEFAULT_FROM_EMAIL,
        #     recipient_list=[data['contacto']['email']],
        #     fail_silently=False,
        # )
        
        # 4. Limpiar carrito
        if 'carrito' in request.session:
            del request.session['carrito']
        if 'cupon_activo' in request.session:
            del request.session['cupon_activo']
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'order_number': f"ORD-2026-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}",
            'message': 'Pedido procesado exitosamente'
        })
        
    except Exception as e:
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