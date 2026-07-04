from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.urls import reverse_lazy
from django.db.models import Q, Sum, Count, F, Avg
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
from datetime import datetime, date, timedelta
from django.db.models.fields.files import ImageFieldFile, FieldFile
import json
import logging
from django.conf import settings

# Modelos
from .models import (
    Clientes, Pedido, Ventas, Cotizaciones, DetalleVenta,
    DetalleCotizacion, Carritos, ItemsCarrito, DetallePedido, MetodosPago,
    Promocion, PromoCombo, ImagenPromocion
)
from inventario.models import Producto, ImagenesProducto, Inventario

# Forms
from .forms import (
    ClienteForm, PedidoForm, VentaForm, CotizacionForm,
    PromocionForm, PromoComboForm
)

from cloudinary.utils import cloudinary_url
from django.conf import settings

logger = logging.getLogger(__name__)

IVA_RATE = Decimal('0.19')


# ============================================
# ENCODER JSON PERSONALIZADO PARA DJANGO
# ============================================

class DjangoCustomEncoder(json.JSONEncoder):
    """Encoder que maneja automáticamente tipos de Django"""
    def default(self, obj):
        if isinstance(obj, (ImageFieldFile, FieldFile)):
            try:
                return obj.url if obj else ''
            except:
                return ''
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def safe_json_dumps(data, **kwargs):
    """Serialización segura para datos de Django"""
    return json.dumps(data, cls=DjangoCustomEncoder, ensure_ascii=False, **kwargs)


# ============================================================================
# HELPERS DE CARRITO
# ============================================================================

def get_or_create_carrito(request):
    """Obtiene o crea carrito para usuario autenticado o sesión anónima."""
    if not request.session.session_key:
        request.session.create()

    if request.user.is_authenticated:
        cliente = Clientes.objects.filter(
            email=request.user.email,
            deleted_at__isnull=True
        ).first()

        if cliente:
            carrito, _ = Carritos.objects.get_or_create(
                cliente=cliente,
                deleted_at__isnull=True,
                defaults={
                    'session_id': request.session.session_key,
                    'created_at': timezone.now(),
                    'updated_at': timezone.now(),
                }
            )
            return carrito

    # Usuario anónimo → usar session_id
    carrito, _ = Carritos.objects.get_or_create(
        session_id=request.session.session_key,
        deleted_at__isnull=True,
        defaults={
            'created_at': timezone.now(),
            'updated_at': timezone.now(),
        }
    )
    return carrito


def _get_carrito_bd(request):
    """Helper: obtiene el carrito BD de la sesión actual (sin crear)."""
    if not request.session.session_key:
        return None

    if request.user.is_authenticated:
        cliente = Clientes.objects.filter(
            email=request.user.email,
            deleted_at__isnull=True
        ).first()
        if cliente:
            return Carritos.objects.filter(
                cliente=cliente,
                deleted_at__isnull=True
            ).first()

    return Carritos.objects.filter(
        session_id=request.session.session_key,
        deleted_at__isnull=True
    ).first()


def _sync_session(request, carrito_bd):
    """Sincroniza la sesión con el estado actual del carrito en BD."""
    items_qs = ItemsCarrito.objects.filter(
        carrito=carrito_bd
    ).select_related('producto')

    carrito = {}
    for item in items_qs:
        pid = str(item.producto.id_producto)
        carrito[pid] = {
            'producto_id': pid,
            'nombre':      item.producto.referencia_producto or item.producto.codigo_producto,
            'precio':      float(item.precio_unitario),
            'cantidad':    item.cantidad,
        }

    request.session['carrito']          = carrito
    request.session['carrito_cantidad'] = sum(i['cantidad'] for i in carrito.values())
    request.session.modified = True



def carrito_compra(request):
    carrito_bd    = _get_carrito_bd(request)
    items         = []
    total_carrito = 0
    total_iva     = 0

    if carrito_bd:
        items_qs = ItemsCarrito.objects.filter(
            carrito=carrito_bd
        ).select_related('producto', 'producto__categoria')

        for item in items_qs:
            prod          = item.producto
            precio_base   = float(item.precio_unitario)
            iva_unitario  = round(precio_base * float(IVA_RATE), 2)
            subtotal_base = round(precio_base * item.cantidad, 2)
            subtotal_iva  = round(iva_unitario * item.cantidad, 2)

            img = ImagenesProducto.objects.filter(
                producto=prod, es_principal=1
            ).first()

            stock_real = Inventario.objects.filter(
                producto=prod,
                estado='DISPONIBLE',
                deleted_at__isnull=True
            ).aggregate(total=Sum('cantidad_disponible'))['total']

            if not stock_real:
                stock_real = Inventario.objects.filter(
                    producto=prod,
                    deleted_at__isnull=True
                ).aggregate(total=Sum('cantidad_disponible'))['total']

            stock_real = stock_real or 99

            items.append({
                'item_id':     item.id_item,
                'producto_id': prod.id_producto,
                'nombre':      prod.referencia_producto or prod.codigo_producto,
                'sku':         prod.codigo_producto,
                'precio_base': precio_base,
                'iva':         subtotal_iva,
                'subtotal':    subtotal_base,
                'cantidad':    item.cantidad,
                'imagen_url':  img.ruta_imagen.url if img and img.ruta_imagen else '/static/img/placeholder.jpg',
                'stock':       stock_real,
            })

            total_carrito += subtotal_base
            total_iva     += subtotal_iva

    # ═══════════════════════════════════════════════════════════════════════
    # PRODUCTOS RECOMENDADOS (4 aleatorios)
    # ═══════════════════════════════════════════════════════════════════════
    
    productos_disponibles = list(
        Producto.objects.filter(
            deleted_at__isnull=True
        ).exclude(
            id_producto__in=[item['producto_id'] for item in items]
        )
    )
    
    if len(productos_disponibles) >= 4:
        productos_recomendados = random.sample(productos_disponibles, 4)
    else:
        productos_recomendados = productos_disponibles
    
    productos_recomendados_data = []
    for p in productos_recomendados:
        img_rec = ImagenesProducto.objects.filter(
            producto=p, es_principal=1
        ).first()
        
        productos_recomendados_data.append({
            'id': p.id_producto,
            'nombre': p.referencia_producto or p.codigo_producto,
            'precio': float(p.precio_producto) if hasattr(p, 'precio_producto') else 0,
            'imagen_url': img_rec.ruta_imagen.url if img_rec and img_rec.ruta_imagen else '/static/img/placeholder.jpg'
        })

    # ═══════════════════════════════════════════════════════════════════════
    # CÁLCULO DATOS WOMPI (para el widget en el carrito)
    # ═══════════════════════════════════════════════════════════════════════
    from pagos import services as wompi
    from pagos.models import PagoWompi

    wompi_data = None
    cliente_datos_completos = False

    es_cliente = request.session.get('cliente_auth', False)
    cliente_id = request.session.get('cliente_id')

    if es_cliente and cliente_id and items:
        try:
            cliente = Clientes.objects.get(id_cliente=cliente_id, deleted_at__isnull=True)
            cliente_datos_completos = True

            total_final     = round(total_carrito + total_iva, 2)
            amount_in_cents = int(total_final * 100)

            referencia = wompi.generar_referencia()
            while PagoWompi.objects.filter(referencia=referencia).exists():
                referencia = wompi.generar_referencia()

            firma = wompi.generar_firma_integridad(
                amount_in_cents=amount_in_cents,
                currency=settings.WOMPI_CURRENCY,
                reference=referencia,
                public_key=settings.WOMPI_PUBLIC_KEY, 
                secreto=settings.WOMPI_INTEGRITY_SECRET
            )

            # Se crea AQUÍ, no en iniciar_transaccion — sin esto, pago_exitoso()
            # y el webhook nunca encuentran la referencia y el pedido se pierde.
            PagoWompi.objects.create(
                referencia=referencia,
                cliente_id=cliente.id_cliente,
                monto=int(total_final),
                monto_centavos=amount_in_cents,
                moneda=settings.WOMPI_CURRENCY,
                estado='PENDIENTE',
                descripcion=f'Compra carrito — cliente {cliente.id_cliente}',
            )

            wompi_data = {
                'public_key':      settings.WOMPI_PUBLIC_KEY,
                'amount_in_cents': amount_in_cents,
                'reference':       referencia,
                'signature':       firma,
                'redirect_url':    request.build_absolute_uri('/pagos/exito/'),
            }
        except Clientes.DoesNotExist:
            pass


    # ═══════════════════════════════════════════════════════════════════════
    # CONTEXT FINAL (UN SOLO RETURN AL FINAL)
    # ═══════════════════════════════════════════════════════════════════════
    context = {
        'carrito_items': items,
        'carrito_cantidad': sum(item['cantidad'] for item in items),
        'total_carrito': total_carrito,
        'total_iva': total_iva,
        'hay_items': len(items) > 0,
        'carrito_items_json': json.dumps(items, default=str),
        'productos_recomendados': productos_recomendados_data,
        'wompi': wompi_data,
        'cliente_datos_completos': cliente_datos_completos,
    }
    
    return render(request, 'pagina/carrito.html', context)


@require_http_methods(["POST"])
def carrito_actualizar(request, item_id):
    try:
        cantidad = int(request.POST.get('cantidad', 1))
        item     = get_object_or_404(ItemsCarrito, id_item=item_id)

        stock_disponible = Inventario.objects.filter(
            producto=item.producto,
            estado='DISPONIBLE',
            deleted_at__isnull=True
        ).aggregate(total=Sum('cantidad_disponible'))['total']

        if not stock_disponible:
            stock_disponible = Inventario.objects.filter(
                producto=item.producto,
                deleted_at__isnull=True
            ).aggregate(total=Sum('cantidad_disponible'))['total']

        stock_disponible = stock_disponible or 99

        if cantidad > stock_disponible:
            return JsonResponse({
                'success': False,
                'error': f'Solo hay {stock_disponible} unidades disponibles'
            }, status=400)

        if cantidad <= 0:
            carrito = item.carrito
            item.delete()
            _sync_session(request, carrito)
        else:
            item.cantidad   = cantidad
            item.updated_at = timezone.now()
            item.save()
            _sync_session(request, item.carrito)

        return JsonResponse({'success': True})

    except Exception as e:
        import traceback
        print(f"ERROR carrito_actualizar: {traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
def carrito_eliminar(request, item_id):
    """Eliminar un ítem del carrito."""
    try:
        item    = get_object_or_404(ItemsCarrito, id_item=item_id)
        carrito = item.carrito
        item.delete()
        _sync_session(request, carrito)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
def carrito_limpiar(request):
    """Vaciar todo el carrito."""
    try:
        carrito_bd = _get_carrito_bd(request)
        if carrito_bd:
            ItemsCarrito.objects.filter(carrito=carrito_bd).delete()
            carrito_bd.updated_at = timezone.now()
            carrito_bd.save()

        request.session['carrito']          = {}
        request.session['carrito_cantidad'] = 0
        request.session.modified = True

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
def carrito_agregar(request):
    """Agregar producto al carrito desde la vista del carrito (recomendaciones)."""
    try:
        producto_id = request.POST.get('producto_id')
        cantidad    = int(request.POST.get('cantidad', 1))

        prod = get_object_or_404(
            Producto,
            id_producto=producto_id,
            estado='DISPONIBLE',
            deleted_at__isnull=True
        )

        carrito_bd = get_or_create_carrito(request)

        item, created = ItemsCarrito.objects.get_or_create(
            carrito=carrito_bd,
            producto=prod,
            defaults={
                'cantidad':        cantidad,
                'precio_unitario': prod.precio_actual,
                'created_at':      timezone.now(),
                'updated_at':      timezone.now(),
            }
        )
        if not created:
            item.cantidad  += cantidad
            item.updated_at = timezone.now()
            item.save()

        _sync_session(request, carrito_bd)

        total_items = ItemsCarrito.objects.filter(
            carrito=carrito_bd
        ).aggregate(total=Sum('cantidad'))['total'] or 0

        return JsonResponse({'success': True, 'cantidad_total': total_items})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ============================================================================
# API ENDPOINTS DEL CARRITO (AJAX desde productos.html)
# ============================================================================

@require_POST
def api_carrito_agregar(request):
    try:
        if request.content_type and 'application/json' in request.content_type:
            data        = json.loads(request.body)
            producto_id = str(data.get('producto_id'))
            cantidad    = int(data.get('cantidad', 1))
        else:
            producto_id = str(request.POST.get('producto_id'))
            cantidad    = int(request.POST.get('cantidad', 1))

        prod = get_object_or_404(
            Producto,
            id_producto=producto_id,
            estado='DISPONIBLE',
            deleted_at__isnull=True
        )

        carrito_bd = get_or_create_carrito(request)

        item, created = ItemsCarrito.objects.get_or_create(
            carrito=carrito_bd,
            producto=prod,
            defaults={
                'cantidad':        cantidad,
                'precio_unitario': prod.precio_actual,
                'created_at':      timezone.now(),
                'updated_at':      timezone.now(),
            }
        )
        if not created:
            item.cantidad  += cantidad
            item.updated_at = timezone.now()
            item.save()

        _sync_session(request, carrito_bd)

        total_items = ItemsCarrito.objects.filter(
            carrito=carrito_bd
        ).aggregate(total=Sum('cantidad'))['total'] or 0

        return JsonResponse({
            'success':        True,
            'cantidad_total': total_items,
            'nombre':         prod.referencia_producto or prod.codigo_producto,
            'precio':         float(prod.precio_actual),
        })

    except Exception as e:
        from django.http import Http404
        if isinstance(e, Http404):
            return JsonResponse({'success': False, 'error': 'Producto no encontrado'}, status=404)
        import traceback
        print(f"ERROR api_carrito_agregar: {traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
def api_carrito_actualizar(request, item_id):
    """API: Actualizar cantidad de un ítem."""
    try:
        if request.content_type and 'application/json' in request.content_type:
            data     = json.loads(request.body)
            cantidad = int(data.get('cantidad') or 1)
        else:
            cantidad = int(request.POST.get('cantidad', 1))

        carrito_bd = get_or_create_carrito(request)
        item       = get_object_or_404(ItemsCarrito, id_item=item_id, carrito=carrito_bd)

        if cantidad < 1:
            item.delete()
        else:
            item.cantidad   = cantidad
            item.updated_at = timezone.now()
            item.save()

        _sync_session(request, carrito_bd)

        total_items = ItemsCarrito.objects.filter(
            carrito=carrito_bd
        ).aggregate(total=Sum('cantidad'))['total'] or 0

        return JsonResponse({'success': True, 'cantidad_total': total_items})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_POST
def api_carrito_eliminar(request, item_id):
    """API: Eliminar un ítem del carrito."""
    try:
        carrito_bd = get_or_create_carrito(request)
        item       = get_object_or_404(ItemsCarrito, id_item=item_id, carrito=carrito_bd)
        item.delete()
        _sync_session(request, carrito_bd)

        total_items = ItemsCarrito.objects.filter(
            carrito=carrito_bd
        ).aggregate(total=Sum('cantidad'))['total'] or 0

        return JsonResponse({'success': True, 'cantidad_total': total_items})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_GET
def api_carrito_contador(request):
    """API: Obtener la cantidad total del carrito."""
    try:
        carrito_bd      = _get_carrito_bd(request)
        carrito_cantidad = 0

        if carrito_bd:
            result           = ItemsCarrito.objects.filter(
                carrito=carrito_bd
            ).aggregate(total=Sum('cantidad'))
            carrito_cantidad = result['total'] or 0

        return JsonResponse({'cantidad': carrito_cantidad})

    except Exception as e:
        return JsonResponse({'cantidad': 0, 'error': str(e)})


@require_GET
def api_carrito_estado(request):
    """Devuelve el estado actual del carrito para actualización en tiempo real."""
    carrito_bd    = _get_carrito_bd(request)
    items         = []
    total_carrito = 0
    total_iva     = 0

    if carrito_bd:
        items_qs = ItemsCarrito.objects.filter(
            carrito=carrito_bd
        ).select_related('producto')

        for item in items_qs:
            prod          = item.producto
            precio_base   = float(item.precio_unitario)
            iva_unitario  = round(precio_base * float(IVA_RATE), 2)
            subtotal_base = round(precio_base * item.cantidad, 2)
            subtotal_iva  = round(iva_unitario * item.cantidad, 2)

            img = ImagenesProducto.objects.filter(
                producto=prod, es_principal=1
            ).first()

            stock_real = Inventario.objects.filter(
                producto=prod,
                estado='DISPONIBLE',
                deleted_at__isnull=True
            ).aggregate(total=Sum('cantidad_disponible'))['total']

            if not stock_real:
                stock_real = Inventario.objects.filter(
                    producto=prod,
                    deleted_at__isnull=True
                ).aggregate(total=Sum('cantidad_disponible'))['total']

            stock_real = stock_real or 99

            items.append({
                'item_id':     item.id_item,
                'producto_id': prod.id_producto,
                'nombre':      prod.referencia_producto or prod.codigo_producto,
                'sku':         prod.codigo_producto,
                'precio_base': precio_base,
                'iva':         subtotal_iva,
                'subtotal':    subtotal_base,
                'subtotal_con_iva': round(subtotal_base + subtotal_iva, 2),
                'cantidad':    item.cantidad,
                'imagen_url':  img.ruta_imagen if img else '/static/img/placeholder.jpg',
                'stock':       stock_real,
            })

            total_carrito += subtotal_base
            total_iva     += subtotal_iva

    return JsonResponse({
        'carrito_items':    items,
        'total_carrito':    round(total_carrito, 2),
        'total_iva':        round(total_iva, 2),
        'total_final':      round(total_carrito + total_iva, 2),
        'carrito_cantidad': sum(i['cantidad'] for i in items),
        'hay_items':        bool(items),
    })


# ============================================================================
# API: Recomendaciones de productos para el carrito
# ============================================================================

import random
def api_carrito_recomendados(request):
    print("🔍 Endpoint api_carrito_recomendados llamado")
    
    try:
        # Obtener productos disponibles
        productos_qs = Producto.objects.filter(disponible=True)
        print(f"📊 Total productos disponibles: {productos_qs.count()}")
        
        productos_disponibles = list(productos_qs)
        
        if len(productos_disponibles) == 0:
            print("⚠️ No hay productos disponibles")
            return JsonResponse({
                'success': True,
                'productos': []
            })
        
        # Seleccionar 4 productos aleatorios
        if len(productos_disponibles) >= 4:
            productos_aleatorios = random.sample(productos_disponibles, 4)
        else:
            productos_aleatorios = productos_disponibles
        
        print(f"✅ Seleccionados {len(productos_aleatorios)} productos aleatorios")
        
        productos_data = []
        for p in productos_aleatorios:
            producto_dict = {
                'id': p.id,
                'nombre': p.nombre,
                'precio': float(p.precio),
                'imagen_url': p.imagen.url if p.imagen else '/static/img/placeholder.jpg'
            }
            productos_data.append(producto_dict)
            print(f"  - Producto: {p.nombre} (${p.precio})")
        
        response_data = {
            'success': True,
            'productos': productos_data
        }
        
        print(f"📤 Enviando respuesta: {response_data}")
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"❌ Error en api_carrito_recomendados: {e}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'success': False,
            'error': str(e),
            'productos': []
        }, status=500)


# ============================================================================
# CLIENTES
# ============================================================================

class ClienteListView(ListView):
    model = Clientes
    template_name = 'ventas/cliente_list.html'
    context_object_name = 'clientes'
    paginate_by = 10

    def get_queryset(self):
        queryset = Clientes.objects.filter(deleted_at__isnull=True)
        estado   = self.request.GET.get('estado')
        busqueda = self.request.GET.get('busqueda')

        if estado:
            queryset = queryset.filter(estado=estado)
        if busqueda:
            queryset = queryset.filter(
                Q(nombre__icontains=busqueda) |
                Q(apellido__icontains=busqueda) |
                Q(email__icontains=busqueda) |
                Q(telefono__icontains=busqueda) |
                Q(direccion__icontains=busqueda)
            )
        return queryset.order_by('-nombre')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados']          = ['ACTIVO', 'INACTIVO']
        context['titulo']           = 'Clientes'
        context['total_clientes']   = Clientes.objects.filter(deleted_at__isnull=True).count()
        context['clientes_activos'] = Clientes.objects.filter(
            estado='ACTIVO', deleted_at__isnull=True
        ).count()
        return context


class ClienteCreateView(CreateView):
    model         = Clientes
    template_name = 'ventas/cliente_form.html'
    form_class    = ClienteForm
    success_url   = reverse_lazy('ventas:cliente_list')

    def get_context_data(self, **kwargs):
        context          = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Cliente'
        return context

    def form_valid(self, form):
        try:
            cliente                = form.save(commit=False)
            cliente.fecha_registro = timezone.now()
            cliente.created_at     = timezone.now()
            cliente.updated_at     = timezone.now()
            if not cliente.estado:
                cliente.estado = 'ACTIVO'
            cliente.save()
            messages.success(
                self.request,
                f'Cliente "{cliente.get_nombre_completo()}" registrado exitosamente.'
            )
            return redirect(self.success_url)
        except ValidationError as e:
            messages.error(self.request, f'Error de validación: {str(e)}')
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f'Error al registrar: {str(e)}')
            return self.form_invalid(form)


class ClienteUpdateView(UpdateView):
    model         = Clientes
    template_name = 'ventas/cliente_form.html'
    form_class    = ClienteForm
    success_url   = reverse_lazy('ventas:cliente_list')

    def get_queryset(self):
        return Clientes.objects.filter(deleted_at__isnull=True)

    def get_context_data(self, **kwargs):
        context          = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Cliente'
        cliente = self.get_object()
        if cliente.tiene_pedidos_asociados():
            messages.info(
                self.request,
                f"Este cliente tiene {cliente.get_cantidad_pedidos()} pedidos asociados"
            )
        return context

    def form_valid(self, form):
        try:
            cliente            = form.save(commit=False)
            cliente.updated_at = timezone.now()
            cliente.save()
            messages.success(
                self.request,
                f'Cliente "{cliente.get_nombre_completo()}" actualizado correctamente.'
            )
            return redirect(self.success_url)
        except ValidationError as e:
            messages.error(self.request, f'Error de validación: {str(e)}')
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f'Error al actualizar: {str(e)}')
            return self.form_invalid(form)


class ClienteDeleteView(View):
    def post(self, request, pk):
        try:
            cliente = get_object_or_404(Clientes, pk=pk, deleted_at__isnull=True)
            if not cliente.puede_eliminarse():
                messages.error(
                    request,
                    "No se puede eliminar. El cliente tiene pedidos activos o pendientes."
                )
                return redirect('ventas:cliente_list')
            cliente.delete()
            messages.success(
                request,
                f'Cliente "{cliente.get_nombre_completo()}" eliminado correctamente.'
            )
            return redirect('ventas:cliente_list')
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('ventas:cliente_list')
        except Exception as e:
            messages.error(request, f'Error al eliminar: {str(e)}')
            return redirect('ventas:cliente_list')


class ClienteDetailView(DetailView):
    model               = Clientes
    template_name       = 'ventas/cliente_detail.html'
    context_object_name = 'cliente'

    def get_queryset(self):
        return Clientes.objects.filter(deleted_at__isnull=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cliente = self.get_object()

        context['total_pedidos'] = Pedido.objects.filter(
            cliente=cliente, deleted_at__isnull=True
        ).count()

        total = Pedido.objects.filter(
            cliente=cliente, deleted_at__isnull=True, estado_pedido='COMPLETADO'
        ).aggregate(total=Sum('total_pedido'))['total'] or 0
        context['total_gastado'] = float(total)

        ultimo = Pedido.objects.filter(
            cliente=cliente, deleted_at__isnull=True
        ).order_by('-fecha_pedido').first()
        context['ultimo_pedido'] = ultimo.fecha_pedido.strftime('%d/%m/%y') if ultimo else None

        context['ultimos_pedidos'] = Pedido.objects.filter(
            cliente=cliente, deleted_at__isnull=True
        ).order_by('-fecha_pedido')[:5]

        return context


class ClienteActivarView(View):
    def post(self, request, pk):
        try:
            cliente = get_object_or_404(Clientes, pk=pk)
            cliente.restore()
            messages.success(
                request,
                f'Cliente "{cliente.get_nombre_completo()}" activado correctamente.'
            )
            return redirect('ventas:cliente_list')
        except Exception as e:
            messages.error(request, f'Error al activar: {str(e)}')
            return redirect('ventas:cliente_list')


class ClienteDesactivarView(View):
    def post(self, request, pk):
        try:
            cliente = get_object_or_404(Clientes, pk=pk, deleted_at__isnull=True)
            cliente.desactivar()
            messages.success(
                request,
                f'Cliente "{cliente.get_nombre_completo()}" desactivado correctamente.'
            )
            return redirect('ventas:cliente_list')
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('ventas:cliente_list')
        except Exception as e:
            messages.error(request, f'Error al desactivar: {str(e)}')
            return redirect('ventas:cliente_list')


# ============================================================================
# PEDIDOS
# ============================================================================

class PedidoListView(ListView):
    model               = Pedido
    template_name       = 'ventas/pedido_list.html'
    context_object_name = 'pedidos'
    paginate_by         = 10

    def get_queryset(self):
        queryset = Pedido.objects.filter(
            deleted_at__isnull=True
        ).select_related('cliente', 'usuario', 'asesor')

        cliente       = self.request.GET.get('cliente')
        estado        = self.request.GET.get('estado')
        fecha_inicio  = self.request.GET.get('fecha_inicio')
        fecha_fin     = self.request.GET.get('fecha_fin')
        entrega_desde = self.request.GET.get('entrega_desde')
        entrega_hasta = self.request.GET.get('entrega_hasta')
        busqueda      = self.request.GET.get('busqueda')

        if cliente:      queryset = queryset.filter(cliente_id=cliente)
        if estado:       queryset = queryset.filter(estado_pedido=estado)
        if fecha_inicio: queryset = queryset.filter(fecha_pedido__gte=fecha_inicio)
        if fecha_fin:    queryset = queryset.filter(fecha_pedido__lte=fecha_fin)
        if entrega_desde:queryset = queryset.filter(fecha_entrega_estimada__gte=entrega_desde)
        if entrega_hasta:queryset = queryset.filter(fecha_entrega_estimada__lte=entrega_hasta)
        if busqueda:
            queryset = queryset.filter(
                Q(numero_pedido__icontains=busqueda) |
                Q(cliente__nombre__icontains=busqueda) |
                Q(cliente__apellido__icontains=busqueda)
            )
        return queryset.order_by('-fecha_pedido', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clientes'] = Clientes.objects.filter(estado='ACTIVO', deleted_at__isnull=True)
        context['estados']  = ['PENDIENTE', 'CONFIRMADO', 'EN PROCESO', 'COMPLETADO', 'CANCELADO']
        context['titulo']   = 'Pedidos'
        context['total_pedidos'] = Pedido.objects.filter(deleted_at__isnull=True).count()
        context['pedidos_pendientes'] = Pedido.objects.filter(
            estado_pedido='PENDIENTE', deleted_at__isnull=True
        ).count()
        return context


class PedidoCreateView(CreateView):
    model         = Pedido
    template_name = 'ventas/pedido_form.html'
    form_class    = PedidoForm
    success_url   = reverse_lazy('ventas:pedido_list')

    def get_context_data(self, **kwargs):
        context          = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Pedido'
        context['clientes'] = Clientes.objects.filter(estado='ACTIVO', deleted_at__isnull=True)
        return context

    def form_valid(self, form):
        try:
            cliente = form.cleaned_data['cliente']
            if cliente.estado != 'ACTIVO':
                messages.error(self.request, "El cliente seleccionado está inactivo.")
                return self.form_invalid(form)

            pedido = form.save(commit=False)
            usuario_id = self.request.session.get('usuario_id')
            if not usuario_id:
                messages.error(self.request, "Debes iniciar sesión para crear un pedido")
                return redirect('usuarios:login')

            pedido.usuario_id    = usuario_id
            pedido.fecha_pedido  = timezone.now()
            pedido.estado_pedido = 'PENDIENTE'
            pedido.total_pedido  = 0
            pedido.save()

            messages.success(
                self.request,
                f"Pedido {pedido.numero_pedido} creado. Ahora agregue los productos."
            )
            return redirect('ventas:pedido_detail', pk=pedido.pk)

        except ValidationError as e:
            messages.error(self.request, f"Error de validación: {str(e)}")
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f"Error al crear el pedido: {str(e)}")
            return self.form_invalid(form)


class PedidoUpdateView(UpdateView):
    model         = Pedido
    template_name = 'ventas/pedido_form.html'
    form_class    = PedidoForm
    success_url   = reverse_lazy('ventas:pedido_list')

    def get_queryset(self):
        return Pedido.objects.filter(deleted_at__isnull=True)

    def get_context_data(self, **kwargs):
        context          = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Pedido'
        context['clientes'] = Clientes.objects.filter(estado='ACTIVO', deleted_at__isnull=True)
        if not self.get_object().puede_modificarse():
            messages.warning(self.request, "Este pedido no puede modificarse por su estado actual")
        return context

    def form_valid(self, form):
        try:
            pedido = self.get_object()
            if not pedido.puede_modificarse():
                messages.error(
                    self.request,
                    f"No se puede modificar un pedido en estado {pedido.estado_pedido}"
                )
                return self.form_invalid(form)

            pedido            = form.save(commit=False)
            pedido.updated_at = timezone.now()
            pedido.save()
            messages.success(self.request, f"Pedido {pedido.numero_pedido} actualizado correctamente")
            return redirect(self.success_url)

        except ValidationError as e:
            messages.error(self.request, f"Error de validación: {str(e)}")
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f"Error al actualizar: {str(e)}")
            return self.form_invalid(form)


class PedidoDeleteView(View):
    def post(self, request, pk):
        try:
            pedido = get_object_or_404(Pedido, pk=pk, deleted_at__isnull=True)
            if not pedido.puede_eliminarse():
                if pedido.estado_pedido != 'PENDIENTE':
                    messages.error(
                        request,
                        f"Solo se pueden eliminar pedidos PENDIENTE. Estado: {pedido.estado_pedido}"
                    )
                else:
                    messages.error(request, "No se puede eliminar porque tiene productos agregados")
                return redirect('ventas:pedido_list')

            pedido.delete()
            messages.success(request, f"Pedido {pedido.numero_pedido} eliminado correctamente")
            return redirect('ventas:pedido_list')

        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('ventas:pedido_list')
        except Exception as e:
            messages.error(request, f"Error al eliminar: {str(e)}")
            return redirect('ventas:pedido_list')


class PedidoDetailView(DetailView):
    model               = Pedido
    template_name       = 'ventas/pedido_detail.html'
    context_object_name = 'pedido'

    def get_queryset(self):
        return Pedido.objects.filter(
            deleted_at__isnull=True
        ).select_related('cliente', 'usuario')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido  = self.get_object()
        context['detalles'] = pedido.detallepedido_set.filter(
            deleted_at__isnull=True
        ).select_related('producto')
        context['puede_modificarse'] = pedido.puede_modificarse()
        context['puede_eliminarse']  = pedido.puede_eliminarse()
        return context


class PedidoAgregarProductoView(View):
    def post(self, request, pk):
        try:
            pedido = get_object_or_404(Pedido, pk=pk, deleted_at__isnull=True)
            if not pedido.puede_modificarse():
                return JsonResponse(
                    {'success': False, 'error': f"El pedido está en estado {pedido.estado_pedido}"},
                    status=400
                )

            data            = json.loads(request.body)
            producto_id     = data.get('producto_id')
            cantidad        = int(data.get('cantidad', 1))
            precio_unitario = Decimal(data.get('precio_unitario', 0))
            producto        = get_object_or_404(Producto, pk=producto_id)

            detalle, created = DetallePedido.objects.get_or_create(
                pedido=pedido,
                producto=producto,
                defaults={'cantidad': cantidad, 'precio_unitario': precio_unitario}
            )
            if not created:
                detalle.cantidad += cantidad
                detalle.save()

            return JsonResponse({
                'success': True,
                'message': 'Producto agregado al pedido',
                'total':   float(pedido.total_pedido)
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class PedidoCambiarEstadoView(View):
    def post(self, request, pk):
        try:
            pedido       = get_object_or_404(Pedido, pk=pk, deleted_at__isnull=True)
            data         = json.loads(request.body)
            nuevo_estado = data.get('estado')
            pedido.cambiar_estado(nuevo_estado, request.user)
            messages.success(request, f"Pedido {pedido.numero_pedido} cambiado a {nuevo_estado}")
            return redirect('ventas:pedido_detail', pk=pk)
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('ventas:pedido_detail', pk=pk)
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('ventas:pedido_detail', pk=pk)


# ============================================================================
# VENTAS
# ============================================================================

class VentaListView(ListView):
    model               = Ventas
    template_name       = 'ventas/venta_list.html'
    context_object_name = 'ventas'
    paginate_by         = 10

    def get_queryset(self):
        queryset = Ventas.objects.filter(
            deleted_at__isnull=True
        ).select_related('cliente', 'usuario', 'metodo_pago', 'pedido')

        cliente      = self.request.GET.get('cliente')
        estado       = self.request.GET.get('estado')
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin    = self.request.GET.get('fecha_fin')

        if cliente:      queryset = queryset.filter(cliente_id=cliente)
        if estado:       queryset = queryset.filter(estado_venta=estado)
        if fecha_inicio: queryset = queryset.filter(fecha_venta__gte=fecha_inicio)
        if fecha_fin:    queryset = queryset.filter(fecha_venta__lte=fecha_fin)

        return queryset.order_by('-fecha_venta', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clientes'] = Clientes.objects.filter(estado='ACTIVO', deleted_at__isnull=True)
        context['estados']  = ['PENDIENTE', 'COMPLETADA', 'CANCELADA']
        context['titulo']   = 'Ventas'
        return context


class VentaCreateView(CreateView):
    model         = Ventas
    template_name = 'ventas/venta_form.html'
    form_class    = VentaForm
    success_url   = reverse_lazy('ventas:venta_list')

    def get_context_data(self, **kwargs):
        context          = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva Venta'
        context['clientes'] = Clientes.objects.filter(estado='ACTIVO', deleted_at__isnull=True)
        context['pedidos']  = Pedido.objects.filter(estado_pedido='COMPLETADO', deleted_at__isnull=True)
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                venta = form.save(commit=False)
                usuario_id = self.request.session.get('usuario_id')
                if not usuario_id:
                    messages.error(self.request, "Debes iniciar sesión")
                    return redirect('usuarios:login')

                venta.usuario_id   = usuario_id
                venta.fecha_venta  = timezone.now()
                venta.estado_venta = 'PENDIENTE'
                venta.save()

                messages.success(
                    self.request,
                    f"Venta {venta.numero_factura} creada. Agregue los productos."
                )
                return redirect('ventas:venta_detail', pk=venta.pk)

        except ValidationError as e:
            messages.error(self.request, f"Error: {str(e)}")
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f"Error al crear: {str(e)}")
            return self.form_invalid(form)


class VentaUpdateView(UpdateView):
    model         = Ventas
    template_name = 'ventas/venta_form.html'
    form_class    = VentaForm
    success_url   = reverse_lazy('ventas:venta_list')

    def get_queryset(self):
        return Ventas.objects.filter(deleted_at__isnull=True)

    def get_context_data(self, **kwargs):
        context          = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Venta'
        if not self.get_object().puede_modificarse():
            messages.warning(self.request, "Esta venta no puede modificarse")
        return context

    def form_valid(self, form):
        try:
            venta = self.get_object()
            if not venta.puede_modificarse():
                messages.error(self.request, f"No se puede modificar una venta {venta.estado_venta}")
                return self.form_invalid(form)

            venta            = form.save(commit=False)
            venta.updated_at = timezone.now()
            venta.save()
            messages.success(self.request, "Venta actualizada correctamente")
            return redirect(self.success_url)

        except Exception as e:
            messages.error(self.request, f"Error: {str(e)}")
            return self.form_invalid(form)


class VentaDeleteView(View):
    def post(self, request, pk):
        try:
            venta = get_object_or_404(Ventas, pk=pk, deleted_at__isnull=True)
            if not venta.puede_eliminarse():
                messages.error(request, "Solo se pueden eliminar ventas PENDIENTE")
                return redirect('ventas:venta_list')

            venta.delete()
            messages.success(request, "Venta eliminada correctamente")
            return redirect('ventas:venta_list')

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('ventas:venta_list')


class VentaDetailView(DetailView):
    model               = Ventas
    template_name       = 'ventas/venta_detail.html'
    context_object_name = 'venta'

    def get_queryset(self):
        return Ventas.objects.filter(
            deleted_at__isnull=True
        ).select_related('cliente', 'usuario')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        venta   = self.get_object()
        context['detalles'] = venta.detalleventa_set.filter(
            deleted_at__isnull=True
        ).select_related('producto')
        return context


class VentaCompletarView(View):
    def post(self, request, pk):
        try:
            venta = get_object_or_404(Ventas, pk=pk, deleted_at__isnull=True)
            if venta.estado_venta != 'PENDIENTE':
                messages.error(request, "Solo se pueden completar ventas pendientes")
                return redirect('ventas:venta_detail', pk=pk)

            with transaction.atomic():
                venta.completar_venta()
                messages.success(request, f"Venta {venta.numero_factura} completada exitosamente")

            return redirect('ventas:venta_detail', pk=pk)

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('ventas:venta_detail', pk=pk)


# ============================================================================
# COTIZACIONES
# ============================================================================

class CotizacionListView(ListView):
    model               = Cotizaciones
    template_name       = 'ventas/cotizacion_list.html'
    context_object_name = 'cotizaciones'
    paginate_by         = 10

    def get_queryset(self):
        queryset = Cotizaciones.objects.filter(
            deleted_at__isnull=True
        ).select_related('cliente', 'usuario')

        cliente      = self.request.GET.get('cliente')
        estado       = self.request.GET.get('estado')
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin    = self.request.GET.get('fecha_fin')
        busqueda     = self.request.GET.get('busqueda')

        if cliente:      queryset = queryset.filter(cliente_id=cliente)
        if estado:       queryset = queryset.filter(estado=estado)
        if fecha_inicio: queryset = queryset.filter(fecha_cotizacion__gte=fecha_inicio)
        if fecha_fin:    queryset = queryset.filter(fecha_cotizacion__lte=fecha_fin)
        if busqueda:
            queryset = queryset.filter(
                Q(numero_cotizacion__icontains=busqueda) |
                Q(cliente__nombre__icontains=busqueda)
            )
        return queryset.order_by('-fecha_cotizacion', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clientes'] = Clientes.objects.filter(estado='ACTIVO', deleted_at__isnull=True)
        context['estados']  = ['borrador', 'enviada', 'aceptada', 'rechazada', 'vencida', 'cancelada']
        context['titulo']   = 'Cotizaciones'
        return context


class CotizacionCreateView(CreateView):
    model         = Cotizaciones
    template_name = 'ventas/cotizacion_form.html'
    form_class    = CotizacionForm
    success_url   = reverse_lazy('ventas:cotizacion_list')

    def get_context_data(self, **kwargs):
        context          = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva Cotización'
        context['clientes'] = Clientes.objects.filter(estado='ACTIVO', deleted_at__isnull=True)
        return context

    def form_valid(self, form):
        try:
            cotizacion = form.save(commit=False)
            usuario_id = self.request.session.get('usuario_id')
            if not usuario_id:
                messages.error(self.request, "Debes iniciar sesión")
                return redirect('usuarios:login')

            cotizacion.usuario_id        = usuario_id
            cotizacion.fecha_cotizacion  = timezone.now().date()
            cotizacion.estado            = 'borrador'
            cotizacion.save()

            messages.success(self.request, f"Cotización {cotizacion.numero_cotizacion} creada")
            return redirect('ventas:cotizacion_detail', pk=cotizacion.pk)

        except Exception as e:
            messages.error(self.request, f"Error: {str(e)}")
            return self.form_invalid(form)


class CotizacionUpdateView(UpdateView):
    model         = Cotizaciones
    template_name = 'ventas/cotizacion_form.html'
    form_class    = CotizacionForm
    success_url   = reverse_lazy('ventas:cotizacion_list')

    def get_queryset(self):
        return Cotizaciones.objects.filter(deleted_at__isnull=True)

    def get_context_data(self, **kwargs):
        context          = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Cotización'
        if not self.get_object().puede_modificarse():
            messages.warning(self.request, "Esta cotización no puede modificarse")
        return context

    def form_valid(self, form):
        try:
            cotizacion = self.get_object()
            if not cotizacion.puede_modificarse():
                messages.error(
                    self.request,
                    f"No se puede modificar una cotización {cotizacion.estado}"
                )
                return self.form_invalid(form)

            cotizacion            = form.save(commit=False)
            cotizacion.updated_at = timezone.now()
            cotizacion.save()
            messages.success(self.request, "Cotización actualizada")
            return redirect(self.success_url)

        except Exception as e:
            messages.error(self.request, f"Error: {str(e)}")
            return self.form_invalid(form)


class CotizacionDeleteView(View):
    def post(self, request, pk):
        try:
            cotizacion = get_object_or_404(Cotizaciones, pk=pk, deleted_at__isnull=True)
            if not cotizacion.puede_eliminarse():
                messages.error(request, "Solo se pueden eliminar cotizaciones en borrador")
                return redirect('ventas:cotizacion_list')

            cotizacion.delete()
            messages.success(request, "Cotización eliminada")
            return redirect('ventas:cotizacion_list')

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('ventas:cotizacion_list')


class CotizacionDetailView(DetailView):
    model               = Cotizaciones
    template_name       = 'ventas/cotizacion_detail.html'
    context_object_name = 'cotizacion'
    pk_url_kwarg        = 'pk'

    def get_queryset(self):
        return Cotizaciones.objects.filter(
            deleted_at__isnull=True
        ).select_related('cliente', 'usuario')

    def get_context_data(self, **kwargs):
        context    = super().get_context_data(**kwargs)
        cotizacion = self.get_object()
        context['detalles'] = cotizacion.detallecotizacion_set.filter(
            deleted_at__isnull=True
        ).select_related('producto')
        return context


class CotizacionEnviarView(View):
    def post(self, request, pk):
        try:
            cotizacion = get_object_or_404(Cotizaciones, pk=pk)
            if cotizacion.estado != 'borrador':
                messages.error(request, "Solo se pueden enviar cotizaciones en borrador")
                return redirect('ventas:cotizacion_detail', pk=pk)

            cotizacion.estado = 'enviada'
            cotizacion.save()
            messages.success(request, f"Cotización {cotizacion.numero_cotizacion} enviada")
            return redirect('ventas:cotizacion_detail', pk=pk)

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('ventas:cotizacion_detail', pk=pk)


class CotizacionAceptarView(View):
    def post(self, request, pk):
        try:
            cotizacion = get_object_or_404(Cotizaciones, pk=pk)
            if cotizacion.estado != 'enviada':
                messages.error(request, "Solo se pueden aceptar cotizaciones enviadas")
                return redirect('ventas:cotizacion_detail', pk=pk)

            cotizacion.estado = 'aceptada'
            cotizacion.save()
            messages.success(request, f"Cotización {cotizacion.numero_cotizacion} aceptada")
            return redirect('ventas:cotizacion_detail', pk=pk)

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('ventas:cotizacion_detail', pk=pk)


class CotizacionConvertirVentaView(View):
    def post(self, request, pk):
        try:
            cotizacion      = get_object_or_404(Cotizaciones, pk=pk)
            puede, mensaje  = cotizacion.puede_convertirse_en_venta()

            if not puede:
                messages.error(request, mensaje)
                return redirect('ventas:cotizacion_detail', pk=pk)

            with transaction.atomic():
                venta = cotizacion.convertir_en_venta(request.user)
                messages.success(request, f"Cotización convertida en venta {venta.numero_factura}")

            return redirect('ventas:venta_detail', pk=venta.pk)

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('ventas:cotizacion_detail', pk=pk)


# ============================================================================
# PERFIL DE USUARIO
# ============================================================================

def perfil_usuario(request):
    """Vista de perfil del cliente"""
    
    if not request.session.get('cliente_auth'):
        messages.warning(request, 'Debes iniciar sesión para ver tu perfil')
        return redirect('pagina:login')
    
    cliente_id = request.session.get('cliente_id')
    
    if not cliente_id:
        messages.error(request, 'No se encontró tu información de cliente')
        return redirect('pagina:login')
    
    try:
        cliente = Clientes.objects.get(
            id_cliente=cliente_id,
            estado='ACTIVO',
            deleted_at__isnull=True
        )
    except Clientes.DoesNotExist:
        for key in ['cliente_id', 'cliente_auth', 'cliente_nombre', 'cliente_email']:
            request.session.pop(key, None)
        messages.error(request, 'Tu cuenta no existe o está inactiva')
        return redirect('pagina:login')
    
    total_pedidos  = Pedido.objects.filter(cliente=cliente).count()
    puntos_lealtad = total_pedidos * 100
    user_level     = min(10, (puntos_lealtad // 500) + 1)
    xp_current     = puntos_lealtad % 500
    xp_next        = 500
    xp_percent     = (xp_current / xp_next) * 100
    xp_to_next     = xp_next - xp_current

    pedidos_recientes = []
    for p in Pedido.objects.filter(cliente=cliente).order_by('-fecha_pedido')[:5]:
        pedidos_recientes.append({
            'id':              p.id_pedido,
            'numero':          p.numero_pedido or f'ORD-{p.pk}',
            'fecha':           p.fecha_pedido,
            'estado':          p.estado_pedido,
            'estado_color':    'success' if p.estado_pedido == 'COMPLETADO' else 'warning',
            'total':           p.total_pedido,
            'total_items':     3,
            'progreso_percent': {
                'PENDIENTE': 25, 'CONFIRMADO': 50,
                'EN PROCESO': 75, 'COMPLETADO': 100
            }.get(p.estado_pedido, 25),
            'estado_detalle': {
                'PENDIENTE': 'Esperando confirmación',
                'CONFIRMADO': 'Preparando envío',
                'EN PROCESO': 'En camino',
                'COMPLETADO': 'Entregado'
            }.get(p.estado_pedido, 'Procesando'),
            'puede_rastrear': p.estado_pedido in ['EN PROCESO', 'CONFIRMADO'],
        })

    context = {
        'cliente':              cliente,
        'total_pedidos':        total_pedidos,
        'wishlist_count':       0,
        'puntos_lealtad':       puntos_lealtad,
        'badges_count':         min(5, total_pedidos // 2),
        'user_level':           user_level,
        'xp_current':           xp_current,
        'xp_next':              xp_next,
        'xp_percent':           xp_percent,
        'xp_to_next':           xp_to_next,
        'pedidos_recientes':    pedidos_recientes,
        'notificaciones_nuevas': 0,
        'last_password_change': getattr(cliente, 'ultimo_login', 'Nunca'),
    }
    
    return render(request, 'pagina/perfil.html', context)


@require_POST
@login_required
def perfil_actualizar(request):
    try:
        cliente = Clientes.objects.filter(
            email=request.user.email, deleted_at__isnull=True
        ).first()
        
        if not cliente:
            return JsonResponse({'success': False, 'error': 'Cliente no encontrado'}, status=404)

        if 'nombre' in request.POST:
            cliente.nombre = request.POST.get('nombre', '').strip()
        
        if 'email' in request.POST:
            cliente.email = request.POST.get('email', '').strip().lower()
        
        if 'telefono' in request.POST:
            cliente.telefono = request.POST.get('telefono', '').strip()
        
        if 'direccion' in request.POST:
            direccion = request.POST.get('direccion', '').strip()
            cliente.direccion = direccion if direccion else None

        if 'fecha_nacimiento' in request.POST:
            fecha_str = request.POST.get('fecha_nacimiento', '').strip()
            if fecha_str:
                try:
                    cliente.fecha_nacimiento = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({
                        'success': False, 
                        'error': 'Formato de fecha inválido. Use AAAA-MM-DD'
                    }, status=400)
            else:
                cliente.fecha_nacimiento = None
        
        cliente.full_clean()
        cliente.save()
        cliente.refresh_from_db()

        return JsonResponse({
            'success': True, 
            'mensaje': 'Perfil actualizado',
            'data': {
                'nombre': cliente.nombre,
                'telefono': cliente.telefono,
                'direccion': cliente.direccion,
                'fecha_nacimiento': cliente.fecha_nacimiento.isoformat() if cliente.fecha_nacimiento else None
            }
        })
        
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error: {str(e)}'}, status=500)


@require_POST
@login_required
def password_cambiar(request):
    try:
        data             = json.loads(request.body)
        current_password = data.get('current_password', '')
        new_password     = data.get('new_password', '')

        if not request.user.check_password(current_password):
            return JsonResponse({'success': False, 'error': 'Contraseña actual incorrecta'}, status=400)
        if len(new_password) < 8:
            return JsonResponse({'success': False, 'error': 'La contraseña debe tener al menos 8 caracteres'}, status=400)

        request.user.set_password(new_password)
        request.user.last_login = timezone.now()
        request.user.save()

        return JsonResponse({'success': True, 'mensaje': 'Contraseña actualizada'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@login_required
def notificaciones_marcar_leidas(request):
    try:
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@login_required
def preferencias_guardar(request):
    try:
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_GET
@login_required
def datos_exportar(request):
    try:
        cliente = Clientes.objects.filter(
            email=request.user.email, deleted_at__isnull=True
        ).first()

        datos = {
            'usuario': {
                'email':           request.user.email,
                'ultimo_acceso':   request.user.last_login.isoformat() if request.user.last_login else None,
            },
            'cliente': {
                'nombre':    cliente.nombre    if cliente else None,
                'telefono':  cliente.telefono  if cliente else None,
                'direccion': cliente.direccion if cliente else None,
            } if cliente else None,
            'pedidos': list(
                Pedido.objects.filter(cliente=cliente).values(
                    'id_pedido', 'numero_pedido', 'fecha_pedido', 'estado_pedido', 'total_pedido'
                )
            ) if cliente else [],
            'exportado_en': timezone.now().isoformat(),
        }

        response = HttpResponse(
            json.dumps(datos, indent=2, ensure_ascii=False, default=str),
            content_type='application/json'
        )
        response['Content-Disposition'] = (
            f'attachment; filename="order-rae-datos-{timezone.now().date()}.json"'
        )
        return response

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_GET
@login_required
def perfil_stats(request):
    try:
        cliente = Clientes.objects.filter(
            email=request.user.email, deleted_at__isnull=True
        ).first()

        return JsonResponse({
            'pedidos':               Pedido.objects.filter(cliente=cliente).count() if cliente else 0,
            'notificaciones_nuevas': 0,
            'puntos_lealtad':        (Pedido.objects.filter(cliente=cliente).count() * 100) if cliente else 0,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ===========================================================================
# PROMOCIONES
# ===========================================================================

class PromocionListView(ListView):
    """Lista de promociones con filtros y estadísticas"""
    model = Promocion
    template_name = 'ventas/promocion_list.html'
    context_object_name = 'promociones'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Promocion.objects.all().prefetch_related('imagenes')
        
        categoria = self.request.GET.get('categoria')
        estado = self.request.GET.get('estado')
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        
        if categoria:
            queryset = queryset.filter(categoria=categoria)
        
        if estado == 'activa':
            queryset = queryset.filter(activa=True)
        elif estado == 'inactiva':
            queryset = queryset.filter(activa=False)
        
        if fecha_inicio:
            queryset = queryset.filter(fecha_inicio__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha_fin__lte=fecha_fin)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        total = Promocion.objects.count()
        activas = Promocion.objects.filter(activa=True).count()
        descuento_promedio = Promocion.objects.filter(activa=True).aggregate(
            avg=Avg('porcentaje_descuento')
        )['avg'] or 0
        
        fecha_limite = timezone.now().date() + timedelta(days=7)
        vencidas = Promocion.objects.filter(
            activa=True,
            fecha_fin__lte=fecha_limite
        ).count()
        
        context['total_promociones'] = total
        context['promociones_activas'] = activas
        context['descuento_promedio'] = round(descuento_promedio, 1)
        context['promociones_vencidas'] = vencidas
        context['titulo'] = 'Promociones'
        
        return context


class PromocionCreateView(CreateView):
    """Crear nueva promoción"""
    model = Promocion
    template_name = 'ventas/promocion_form.html'
    form_class = PromocionForm
    success_url = reverse_lazy('ventas:promocion_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva Promoción'
        context['imagenes_existentes'] = []
        return context
    
    def form_valid(self, form):
        try:
            promocion = form.save(commit=False)
            promocion.created_at = timezone.now()
            promocion.updated_at = timezone.now()
            
            if promocion.precio_promo >= promocion.precio_original:
                messages.error(
                    self.request,
                    "El precio promocional debe ser menor al precio original"
                )
                return self.form_invalid(form)
            
            promocion.save()
            
            # Guardar imágenes
            self._guardar_imagenes(promocion)
            
            messages.success(
                self.request,
                f'Promoción "{promocion.nombre}" creada exitosamente.'
            )
            return redirect(self.success_url)
        except ValidationError as e:
            messages.error(self.request, f'Error de validación: {str(e)}')
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f'Error al crear: {str(e)}')
            return self.form_invalid(form)
    
    def _guardar_imagenes(self, promocion):
        """Guarda las imágenes subidas"""
        nuevas_imagenes = self.request.FILES.getlist('nuevas_imagenes')
        imagen_principal_index = int(self.request.POST.get('imagen_principal_index', 0))
        
        for i, imagen in enumerate(nuevas_imagenes):
            ImagenPromocion.objects.create(
                promocion=promocion,
                ruta_imagen=imagen,
                es_principal=1 if i == imagen_principal_index else 0
            )


class PromocionDetailView(DetailView):
    """Detalle de una promoción"""
    model = Promocion
    template_name = 'ventas/promocion_detail.html'
    context_object_name = 'promocion'
    
    def get_queryset(self):
        return Promocion.objects.all()


class PromocionUpdateView(UpdateView):
    """Editar promoción existente"""
    model = Promocion
    template_name = 'ventas/promocion_form.html'
    form_class = PromocionForm
    success_url = reverse_lazy('ventas:promocion_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Promoción'
        context['imagenes_existentes'] = ImagenPromocion.objects.filter(
            promocion=self.object
        )
        return context
    
    def form_valid(self, form):
        try:
            promocion = form.save(commit=False)
            promocion.updated_at = timezone.now()
            
            if promocion.precio_promo >= promocion.precio_original:
                messages.error(
                    self.request,
                    "El precio promocional debe ser menor al precio original"
                )
                return self.form_invalid(form)
            
            promocion.save()
            
            # Eliminar imágenes marcadas
            self._eliminar_imagenes()
            
            # Guardar nuevas imágenes
            self._guardar_imagenes(promocion)
            
            messages.success(
                self.request,
                f'Promoción "{promocion.nombre}" actualizada correctamente.'
            )
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'Error al actualizar: {str(e)}')
            return self.form_invalid(form)
    
    def _eliminar_imagenes(self):
        """Elimina las imágenes marcadas para eliminación"""
        imagenes_a_eliminar = self.request.POST.getlist('imagenes_a_eliminar')
        for id_imagen in imagenes_a_eliminar:
            if id_imagen:
                try:
                    imagen = ImagenPromocion.objects.get(id_imagen=id_imagen)
                    imagen.ruta_imagen.delete()  # Elimina el archivo
                    imagen.delete()
                except ImagenPromocion.DoesNotExist:
                    pass
    
    def _guardar_imagenes(self, promocion):
        """Guarda las nuevas imágenes subidas"""
        nuevas_imagenes = self.request.FILES.getlist('nuevas_imagenes')
        imagen_principal_index = int(self.request.POST.get('imagen_principal_index', 0))
        
        # Contar imágenes existentes
        imagenes_existentes = ImagenPromocion.objects.filter(promocion=promocion).count()
        
        for i, imagen in enumerate(nuevas_imagenes):
            ImagenPromocion.objects.create(
                promocion=promocion,
                ruta_imagen=imagen,
                es_principal=1 if (imagenes_existentes + i) == imagen_principal_index else 0
            )


class PromocionDeleteView(View):
    """Eliminar promoción"""
    def post(self, request, pk):
        try:
            promocion = get_object_or_404(Promocion, pk=pk)
            nombre = promocion.nombre
            promocion.delete()
            messages.success(
                request,
                f'Promoción "{nombre}" eliminada correctamente.'
            )
            return redirect('ventas:promocion_list')
        except Exception as e:
            messages.error(request, f'Error al eliminar: {str(e)}')
            return redirect('ventas:promocion_list')


# ============================================================================
# PROMO COMBOS
# ============================================================================

class PromoComboListView(ListView):
    """Lista de combos promocionales"""
    model = PromoCombo
    template_name = 'ventas/promo_combo_list.html'
    context_object_name = 'combos'
    paginate_by = 10
    
    def get_queryset(self):
        return PromoCombo.objects.all().order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Combos Promocionales'
        context['total_combos'] = PromoCombo.objects.count()
        context['combos_activos'] = PromoCombo.objects.filter(activa=True).count()
        return context


class PromoComboCreateView(CreateView):
    """Crear nuevo combo"""
    model = PromoCombo
    template_name = 'ventas/promo_combo_form.html'
    form_class = PromoComboForm
    success_url = reverse_lazy('ventas:promo_combo_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Combo Promocional'
        return context
    
    def form_valid(self, form):
        try:
            combo = form.save(commit=False)
            combo.created_at = timezone.now()
            combo.updated_at = timezone.now()
            
            if combo.precio >= combo.precio_original:
                messages.error(
                    self.request,
                    "El precio del combo debe ser menor al precio original"
                )
                return self.form_invalid(form)
            
            combo.save()
            messages.success(
                self.request,
                f'Combo "{combo.nombre}" creado exitosamente.'
            )
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'Error: {str(e)}')
            return self.form_invalid(form)


class PromoComboUpdateView(UpdateView):
    """Editar combo"""
    model = PromoCombo
    template_name = 'ventas/promo_combo_form.html'
    form_class = PromoComboForm
    success_url = reverse_lazy('ventas:promo_combo_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Combo Promocional'
        return context


class PromoComboDeleteView(View):
    """Eliminar combo"""
    def post(self, request, pk):
        try:
            combo = get_object_or_404(PromoCombo, pk=pk)
            nombre = combo.nombre
            combo.delete()
            messages.success(request, f'Combo "{nombre}" eliminado.')
            return redirect('ventas:promo_combo_list')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('ventas:promo_combo_list')


# ============================================================================
# VISTA PÚBLICA DE PROMOCIONES
# ============================================================================

def promociones_view(request):
    """Vista pública para la página de promociones (clientes)"""
    
    promociones_qs = Promocion.objects.filter(activa=True).prefetch_related('imagenes')
    
    promociones = []
    for promo in promociones_qs:
        # USAR la imagen principal desde ImagenPromocion (relación real)
        imagen_principal = promo.imagen_principal
        
        if imagen_principal and imagen_principal.ruta_imagen:
            # MediaCloudinaryStorage ya devuelve una URL completa, lista para usar
            imagen_url = imagen_principal.ruta_imagen.url
        else:
            imagen_url = '/static/img/placeholder.jpg'
        
        promociones.append({
            'id': promo.id_promocion,
            'nombre': promo.nombre,
            'descripcion': promo.descripcion or '',
            'categoria': promo.categoria,
            'precio_original': float(promo.precio_original),
            'precio_promo': float(promo.precio_promo),
            'porcentaje_descuento': float(promo.porcentaje_descuento) if promo.porcentaje_descuento else 0,
            'imagen_url': imagen_url,
            'ahorro': float(promo.ahorro),
            'fecha_inicio': promo.fecha_inicio.isoformat() if promo.fecha_inicio else None,
            'fecha_fin': promo.fecha_fin.isoformat() if promo.fecha_fin else None,
        })
    
    combo = PromoCombo.objects.filter(activa=True).first()
    
    if combo:
        imagen_combo = combo.imagen_url or '/static/img/Sofá5.jpg'
        
        promo_combo = {
            'id': combo.id_combo,
            'nombre': combo.nombre,
            'descripcion': combo.descripcion or '',
            'precio': float(combo.precio),
            'precio_original': float(combo.precio_original),
            'ahorro': float(combo.ahorro) if combo.ahorro else 0,
            'porcentaje_descuento': float(combo.porcentaje_descuento) if combo.porcentaje_descuento else 0,
            'imagen_url': imagen_combo,
            'fecha_inicio': combo.fecha_inicio.isoformat() if combo.fecha_inicio else None,
            'fecha_fin': combo.fecha_fin.isoformat() if combo.fecha_fin else None,
        }
    else:
        promo_combo = {
            'id': None,
            'nombre': 'Combo Premium',
            'descripcion': '',
            'precio': 2490000,
            'precio_original': 3290000,
            'ahorro': 800000,
            'porcentaje_descuento': 24,
            'imagen_url': '/static/img/Sofá5.jpg',
        }
    
    carrito_cantidad = request.session.get('carrito_cantidad', 0)
    
    context = {
        'promociones': promociones,
        'promociones_json': json.dumps(promociones, ensure_ascii=False),
        'promo_combo': promo_combo,
        'carrito_cantidad': carrito_cantidad,
        'notificaciones_nuevas': 0,
    }
    
    return render(request, 'ventas/promociones.html', context)