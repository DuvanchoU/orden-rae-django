# 📁 pagina/views.py

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import IntegrityError
import hashlib
import json
import re

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


# =============================================================================
# API ENDPOINTS PARA AJAX - URLs deben coincidir con el JavaScript
# =============================================================================

@require_http_methods(["POST"])
def api_agregar_carrito(request):
    """Agregar producto al carrito vía API - URL: /pagina/api/carrito/agregar/"""
    try:
        data = json.loads(request.body)
        carrito = request.session.get('carrito', {})
        producto_id = str(data.get('producto_id'))
        cantidad = data.get('cantidad', 1)
        precio = data.get('precio', 0)
        
        if not producto_id:
            return JsonResponse({'success': False, 'error': 'producto_id requerido'}, status=400)
        
        if producto_id in carrito:
            carrito[producto_id]['cantidad'] += cantidad
        else:
            carrito[producto_id] = {
                'cantidad': cantidad,
                'precio': precio,
                'nombre': data.get('nombre', 'Producto')
            }
        
        request.session['carrito'] = carrito
        request.session['carrito_cantidad'] = sum(item['cantidad'] for item in carrito.values())
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'cantidad_total': request.session['carrito_cantidad'],
            'message': 'Producto añadido al carrito'
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
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