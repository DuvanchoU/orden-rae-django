import json
import logging

from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from .models import PagoWompi
from . import services as wompi

logger = logging.getLogger(__name__)



# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────

def _get_cliente(request):
    """
    Obtiene el cliente autenticado usando el MISMO criterio que el resto del
    sitio (pagina.views.checkout, pagina.views.api_checkout_procesar):
    sesión manual, NO django.contrib.auth. El login de clientes nunca llama
    a auth.login(), por lo que request.user.is_authenticated es False para
    ellos y @login_required los redirige a /login/ en vez de devolver JSON.
    """
    from ventas.models import Clientes

    cliente_id = request.session.get('cliente_id')
    es_cliente = request.session.get('cliente_auth', False)
    if not es_cliente or not cliente_id:
        return None

    return Clientes.objects.filter(
        id_cliente=cliente_id, estado='ACTIVO', deleted_at__isnull=True
    ).first()


def _get_carrito_items(request):
    from ventas.models import Carritos, ItemsCarrito
    from inventario.models import Producto

    carrito_bd = None
    cliente = _get_cliente(request)
    if cliente:
        carrito_bd = Carritos.objects.filter(
            cliente=cliente, deleted_at__isnull=True
        ).first()

    if not carrito_bd and request.session.session_key:
        carrito_bd = Carritos.objects.filter(
            session_id=request.session.session_key, deleted_at__isnull=True
        ).first()

    items_data = []
    if carrito_bd:
        for item in ItemsCarrito.objects.filter(carrito=carrito_bd).select_related('producto'):
            if item.producto and item.cantidad > 0:
                items_data.append({
                    'producto':        item.producto,
                    'cantidad':        item.cantidad,
                    'precio_unitario': Decimal(str(item.precio_unitario)),
                })
    else:
        carrito_session = request.session.get('carrito', {})
        prods = Producto.objects.filter(
            id_producto__in=list(carrito_session.keys()),
            estado='DISPONIBLE', deleted_at__isnull=True
        )
        mapa = {str(p.id_producto): p for p in prods}
        for pid, dato in carrito_session.items():
            prod = mapa.get(pid)
            if not prod:
                continue
            cantidad = int(dato.get('cantidad', 1)) if isinstance(dato, dict) else int(dato)
            items_data.append({
                'producto':        prod,
                'cantidad':        cantidad,
                'precio_unitario': Decimal(str(prod.precio_actual)),
            })
    return items_data


def _get_carrito_items_por_cliente(cliente):
    """Igual que _get_carrito_items pero sin depender de `request` (lo usa el webhook)."""
    from ventas.models import Carritos, ItemsCarrito
    carrito_bd = Carritos.objects.filter(cliente=cliente, deleted_at__isnull=True).first()
    items_data = []
    if carrito_bd:
        for item in ItemsCarrito.objects.filter(carrito=carrito_bd).select_related('producto'):
            if item.producto and item.cantidad > 0:
                items_data.append({
                    'producto':        item.producto,
                    'cantidad':        item.cantidad,
                    'precio_unitario': Decimal(str(item.precio_unitario)),
                })
    return items_data, carrito_bd


def _calcular_totales(items_data, cupon=None):
    Q = Decimal('0.01')
    subtotal = sum(
        (i['precio_unitario'] * i['cantidad']).quantize(Q, rounding=ROUND_HALF_UP)
        for i in items_data
    ).quantize(Q, rounding=ROUND_HALF_UP)

    impuesto  = (subtotal * Decimal('0.19')).quantize(Q, rounding=ROUND_HALF_UP)
    descuento = Decimal('0.00')

    if cupon:
        tipo  = cupon.get('tipo', '')
        valor = Decimal(str(cupon.get('valor', 0)))
        total_con_iva = (subtotal + impuesto).quantize(Q, rounding=ROUND_HALF_UP)
        if tipo == 'porcentaje':
            descuento = (total_con_iva * valor / 100).quantize(Q, rounding=ROUND_HALF_UP)
        elif tipo == 'fijo':
            descuento = min(valor, total_con_iva).quantize(Q, rounding=ROUND_HALF_UP)

    total = (subtotal + impuesto - descuento).quantize(Q, rounding=ROUND_HALF_UP)

    return {'subtotal': subtotal, 'impuesto': impuesto, 'descuento': descuento, 'total': total}


def _cop_a_centavos(monto_cop: Decimal) -> int:
    """
    Wompi SIEMPRE usa centavos (a diferencia del zero-decimal de Stripe).
    Ej: $50.000 COP -> amount_in_cents = 5000000
    """
    pesos = int(monto_cop.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return pesos * 100


# ──────────────────────────────────────────────────────────────────────────
# DEBUG — solo con DEBUG=True
# ──────────────────────────────────────────────────────────────────────────

@require_GET
def debug_wompi(request):
    """GET /pagos/debug-wompi/  — verifica configuración. Solo en DEBUG=True."""
    if not getattr(settings, 'DEBUG', False):
        return HttpResponse('No disponible en producción', status=403)

    pk   = getattr(settings, 'WOMPI_PUBLIC_KEY', '')
    pvk  = getattr(settings, 'WOMPI_PRIVATE_KEY', '')
    isec = getattr(settings, 'WOMPI_INTEGRITY_SECRET', '')
    esec = getattr(settings, 'WOMPI_EVENTS_SECRET', '')

    api_ok, api_err = False, ''
    try:
        api_ok = bool(wompi.verificar_merchant(pk)) if pk else False
    except Exception as e:
        api_err = str(e)

    return JsonResponse({
        'WOMPI_PUBLIC_KEY':       f'{pk[:18]}…' if pk else '❌ NO CONFIGURADA',
        'WOMPI_PRIVATE_KEY':      f'{pvk[:18]}…' if pvk else '❌ NO CONFIGURADA',
        'WOMPI_INTEGRITY_SECRET': f'{isec[:18]}…' if isec else '❌ NO CONFIGURADA',
        'WOMPI_EVENTS_SECRET':    f'{esec[:18]}…' if esec else '⚠️ No configurada',
        'pk_es_sandbox':          pk.startswith('pub_test_') if pk else False,
        'base_url':               getattr(settings, 'WOMPI_BASE_URL', ''),
        'api_conecta_ok':         api_ok,
        'api_error':              api_err,
        # NUEVO: refleja exactamente lo que ve iniciar_transaccion para este request
        'sesion_cliente_auth':    request.session.get('cliente_auth', False),
        'sesion_cliente_id':      request.session.get('cliente_id'),
    })


# ──────────────────────────────────────────────────────────────────────────
# ENDPOINT 1: Iniciar transacción (genera referencia + firma para el Widget)
# ──────────────────────────────────────────────────────────────────────────

@require_POST
def iniciar_transaccion(request):
    """POST /pagos/iniciar-transaccion/"""
    if not getattr(settings, 'WOMPI_PUBLIC_KEY', '') or not getattr(settings, 'WOMPI_INTEGRITY_SECRET', ''):
        logger.error('WOMPI_PUBLIC_KEY / WOMPI_INTEGRITY_SECRET no configuradas')
        return JsonResponse(
            {'error': 'Pasarela de pago no configurada. Contacta al administrador.'},
            status=500
        )

    cliente = _get_cliente(request)
    if not cliente:
        return JsonResponse({'error': 'Debes iniciar sesión para continuar.'}, status=401)

    try:
        body     = json.loads(request.body or '{}')
        cupon    = body.get('cupon') or request.session.get('cupon_activo')
        contacto = body.get('contacto', {})
        envio    = body.get('envio', {})

        items, _ = _get_carrito_items_por_cliente(cliente)
        if not items:
            items = _get_carrito_items(request)
        if not items:
            return JsonResponse({'error': 'El carrito está vacío'}, status=400)

        totales         = _calcular_totales(items, cupon)
        amount_in_cents = _cop_a_centavos(totales['total'])

        if amount_in_cents < 150000:
            return JsonResponse(
                {'error': f'Monto mínimo: $1.500 COP (actual: ${amount_in_cents // 100})'},
                status=400
            )

        desc = ', '.join(
            f"{i['producto'].referencia_producto or i['producto'].codigo_producto} x{i['cantidad']}"
            for i in items[:5]
        )

        referencia = wompi.generar_referencia()
        # Colisión de referencia es extremadamente improbable, pero es gratis blindarlo
        while PagoWompi.objects.filter(referencia=referencia).exists():
            referencia = wompi.generar_referencia()

        firma = wompi.generar_firma_integridad(
            amount_in_cents=amount_in_cents,
            currency=settings.WOMPI_CURRENCY,
            reference=referencia,
            public_key=settings.WOMPI_PUBLIC_KEY,  
            secreto=settings.WOMPI_INTEGRITY_SECRET
        )

        # ── Esta es la pieza que faltaba ──────────────────────────────────
        # Sin este registro, confirmar_pago() y wompi_webhook() nunca
        # encuentran la referencia y el Pedido/Venta jamás se crea, aunque
        # el pago haya sido aprobado por Wompi.
        PagoWompi.objects.create(
            referencia=referencia,
            cliente_id=cliente.id_cliente,
            monto=int(totales['total']),
            monto_centavos=amount_in_cents,
            moneda='COP',
            estado='PENDIENTE',
            descripcion=desc,
            checkout_data_json=json.dumps(
                {'contacto': contacto, 'envio': envio}, ensure_ascii=False
            ),
        )

        logger.info(f'Iniciando transacción Wompi: ref={referencia} amount_in_cents={amount_in_cents}')

        return JsonResponse({
            'public_key':           settings.WOMPI_PUBLIC_KEY,
            'referencia':           referencia,
            'amount_in_cents':      amount_in_cents,
            'currency':             'COP',
            'signature':            firma,
            'total':                float(totales['total']),
            'subtotal':             float(totales['subtotal']),
            'impuesto':             float(totales['impuesto']),
            'impuesto_en_centavos': _cop_a_centavos(totales['impuesto']),
            'descuento':            float(totales['descuento']),
            'redirect_url':         request.build_absolute_uri('/pagos/exito/'),
        })

    except Exception as e:
        logger.exception('Error inesperado en iniciar_transaccion')
        return JsonResponse({'error': str(e)}, status=500)


# ──────────────────────────────────────────────────────────────────────────
# Lógica compartida: crea Pedido + Venta cuando Wompi aprueba el pago.
# La usan tanto confirmar_pago (camino normal) como el webhook (respaldo /
# métodos asíncronos como PSE). Es idempotente.
# ──────────────────────────────────────────────────────────────────────────

def _completar_compra_si_aprobado(pago_reg, tx_wompi):
    from ventas.models import (
        Clientes, Ventas, DetalleVenta, MetodosPago,
        Pedido, DetallePedido, ItemsCarrito, Carritos,
    )
    from usuarios.models import Usuarios

    if pago_reg.venta_id:
        return pago_reg  # ya procesado — evita duplicar pedidos

    cliente = Clientes.objects.filter(pk=pago_reg.cliente_id, deleted_at__isnull=True).first()
    if not cliente:
        raise ValueError('Cliente no encontrado para el pago')

    items, carrito_bd = _get_carrito_items_por_cliente(cliente)
    if not items:
        raise ValueError('Carrito vacío al confirmar el pago')

    checkout_data = json.loads(pago_reg.checkout_data_json or '{}')
    contacto = checkout_data.get('contacto', {})
    envio    = checkout_data.get('envio', {})

    dirs            = [envio.get('ciudad', ''), envio.get('direccion', ''), envio.get('apartamento', '')]
    direccion_envio = ' - '.join(d.strip() for d in dirs if d and d.strip())
    observaciones   = (
        f"Pedido web | Wompi ref: {pago_reg.referencia} | TX: {pago_reg.wompi_transaction_id} | "
        f"{contacto.get('nombre', '')} {contacto.get('telefono', '')} | {direccion_envio}"
    )
    instrucciones = (envio.get('instrucciones') or '').strip()
    if instrucciones:
        observaciones += f" | {instrucciones}"

    cupon   = None
    totales = _calcular_totales(items, cupon)

    ahora         = timezone.now()
    fecha_entrega = (ahora + timezone.timedelta(days=5)).date()

    metodo_pago, _ = MetodosPago.objects.get_or_create(
        nombre='Wompi',
        defaults={
            'descripcion': 'Pago en línea vía Wompi (Tarjeta / PSE / Nequi)',
            'created_at':  ahora,
            'updated_at':  ahora,
        }
    )

    with transaction.atomic():
        usuario_sistema = Usuarios.objects.filter(pk=1).first()

        ult_p = Pedido.objects.filter(deleted_at__isnull=True).order_by('-id_pedido').first()
        cp    = (ult_p.id_pedido if ult_p else 0) + 1
        num_p = f"PED-{cp:06d}"
        while Pedido.objects.filter(numero_pedido=num_p).exists():
            cp += 1
            num_p = f"PED-{cp:06d}"

        pedido = Pedido(
            cliente=cliente,
            usuario=usuario_sistema,
            asesor=None,
            fecha_pedido=ahora,
            fecha_entrega_estimada=fecha_entrega,
            total_pedido=totales['total'],
            estado_pedido='PENDIENTE',
            estado_facturacion='NO_FACTURADO',
            direccion_entrega=direccion_envio,
            numero_pedido=num_p,
            created_at=ahora,
            updated_at=ahora,
        )
        pedido.save()

        for item in items:
            sub = (item['precio_unitario'] * item['cantidad']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            DetallePedido(
                pedido=pedido, producto=item['producto'], cantidad=item['cantidad'],
                precio_unitario=item['precio_unitario'], subtotal=sub,
                created_at=ahora, updated_at=ahora,
            ).save()

        ult_v = Ventas.objects.filter(prefijo='FAC', deleted_at__isnull=True).order_by('-id_venta').first()
        cv    = (ult_v.id_venta if ult_v else 0) + 1
        num_f = f"FAC-{cv:06d}"
        while Ventas.objects.filter(numero_factura=num_f).exists():
            cv += 1
            num_f = f"FAC-{cv:06d}"

        venta = Ventas(
            usuario=usuario_sistema, cliente=cliente, pedido=pedido,
            tipo_venta='DIRECTA', fecha_venta=ahora,
            subtotal=totales['subtotal'], impuesto=totales['impuesto'],
            descuento=totales['descuento'], total=totales['total'],
            estado_venta='PENDIENTE', metodo_pago=metodo_pago,
            observaciones=observaciones, numero_factura=num_f, prefijo='FAC',
            created_at=ahora, updated_at=ahora,
        )
        venta.save()

        for item in items:
            sub = (item['precio_unitario'] * item['cantidad']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            DetalleVenta(
                venta=venta, producto=item['producto'], cantidad=item['cantidad'],
                precio_unitario=item['precio_unitario'], descuento=Decimal('0.00'),
                subtotal=sub, costo_estimado=None, created_at=ahora, updated_at=ahora,
            ).save()

        pago_reg.estado       = 'COMPLETADO'
        pago_reg.venta_id     = venta.id_venta
        pago_reg.pedido_id    = pedido.id_pedido
        pago_reg.confirmed_at = ahora
        pago_reg.save()

        if direccion_envio and not getattr(cliente, 'direccion', None):
            Clientes.objects.filter(pk=cliente.pk).update(direccion=direccion_envio, updated_at=ahora)

        if carrito_bd:
            ItemsCarrito.objects.filter(carrito=carrito_bd).delete()
            Carritos.objects.filter(pk=carrito_bd.pk).update(deleted_at=ahora, updated_at=ahora)

    logger.info(f'Compra OK vía Wompi: {venta.numero_factura} / {pedido.numero_pedido}')
    return pago_reg


# ──────────────────────────────────────────────────────────────────────────
# ENDPOINT 2: Confirmar pago — llamado por el frontend tras cerrar el Widget
# ──────────────────────────────────────────────────────────────────────────

@require_POST
def confirmar_pago(request):
    """POST /pagos/confirmar-pago/  body: {transaction_id, referencia}"""
    cliente = _get_cliente(request)
    if not cliente:
        return JsonResponse({'error': 'Debes iniciar sesión para continuar.'}, status=401)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Datos JSON inválidos'}, status=400)

    transaction_id = (data.get('transaction_id') or '').strip()
    referencia     = (data.get('referencia') or '').strip()
    if not transaction_id or not referencia:
        return JsonResponse({'error': 'transaction_id y referencia son requeridos'}, status=400)

    pago_reg = PagoWompi.objects.filter(referencia=referencia, cliente_id=cliente.id_cliente).first()
    if not pago_reg:
        return JsonResponse({'error': 'Referencia de pago no encontrada'}, status=404)

    # Idempotencia
    if pago_reg.estado == 'COMPLETADO' and pago_reg.venta_id:
        return JsonResponse({
            'success':       True,
            'order_number':  f"FAC-{pago_reg.venta_id:06d}",
            'pedido_number': f"PED-{pago_reg.pedido_id:06d}" if pago_reg.pedido_id else '',
            'total':         float(pago_reg.monto),
            'message':       'Pago ya procesado anteriormente',
        })

    # Nunca confiar en el estado que reporta el frontend: se verifica contra Wompi.
    try:
        tx = wompi.consultar_transaccion(transaction_id)
    except wompi.WompiError as e:
        return JsonResponse({'error': f'No se pudo verificar el pago con Wompi: {e}'}, status=502)

    estado_wompi = tx.get('status')
    pago_reg.wompi_transaction_id = tx.get('id', transaction_id)
    pago_reg.payment_method_type  = tx.get('payment_method_type', '')
    pago_reg.estado_wompi_raw     = estado_wompi
    pago_reg.metadata_json        = json.dumps(tx)[:9000]

    if estado_wompi != 'APPROVED':
        if estado_wompi in ('DECLINED', 'ERROR'):
            pago_reg.estado        = 'FALLIDO'
            pago_reg.failed_at     = timezone.now()
            pago_reg.error_message = tx.get('status_message', '')
        elif estado_wompi == 'VOIDED':
            pago_reg.estado = 'CANCELADO'
        else:
            pago_reg.estado = 'PENDIENTE'  # ej. PSE en proceso — el webhook lo confirmará luego
        pago_reg.save()
        return JsonResponse(
            {'error': f'Pago no aprobado (estado: {estado_wompi})', 'status': estado_wompi},
            status=400
        )

    pago_reg.save()

    try:
        pago_reg = _completar_compra_si_aprobado(pago_reg, tx)
    except ValueError as e:
        logger.exception('Error creando pedido/venta tras pago aprobado')
        return JsonResponse({'error': str(e)}, status=400)

    request.session['carrito']          = {}
    request.session['carrito_cantidad'] = 0
    request.session.pop('cupon_activo', None)
    request.session.modified = True

    return JsonResponse({
        'success':       True,
        'order_number':  f"FAC-{pago_reg.venta_id:06d}",
        'pedido_number': f"PED-{pago_reg.pedido_id:06d}",
        'total':         float(pago_reg.monto),
        'items':         0,
        'message':       '¡Pedido creado exitosamente!',
    })


# ──────────────────────────────────────────────────────────────────────────
# ENDPOINT 3: Webhook (Wompi -> tu servidor)
# ──────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def wompi_webhook(request):
    """POST /pagos/webhook/ — configúralo en el Dashboard de Wompi (Sandbox y Producción por separado)."""
    try:
        event = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return HttpResponse(status=400)

    if not wompi.verificar_checksum_evento(event):
        logger.warning('Webhook Wompi con checksum inválido — posible spoofing, se descarta')
        return HttpResponse(status=400)

    tx         = event.get('data', {}).get('transaction', {})
    tx_id      = tx.get('id')
    tx_status  = tx.get('status')
    referencia = tx.get('reference')

    logger.info(f'Webhook Wompi: {event.get("event")} -> tx={tx_id} status={tx_status} ref={referencia}')

    pago_reg = PagoWompi.objects.filter(referencia=referencia).first()
    if not pago_reg:
        logger.warning(f'Webhook Wompi: referencia {referencia} no encontrada en BD')
        return HttpResponse(status=200)  # 200 para que Wompi no reintente indefinidamente

    pago_reg.wompi_transaction_id = tx_id
    pago_reg.payment_method_type  = tx.get('payment_method_type', '')
    pago_reg.estado_wompi_raw     = tx_status
    pago_reg.metadata_json        = json.dumps(tx)[:9000]

    if tx_status == 'APPROVED':
        pago_reg.save()
        try:
            _completar_compra_si_aprobado(pago_reg, tx)
        except ValueError:
            logger.exception('Webhook: no se pudo completar la compra (carrito vacío o cliente inválido)')
    elif tx_status in ('DECLINED', 'ERROR'):
        pago_reg.estado        = 'FALLIDO'
        pago_reg.failed_at     = timezone.now()
        pago_reg.error_message = tx.get('status_message', '')
        pago_reg.save()
    elif tx_status == 'VOIDED':
        pago_reg.estado = 'CANCELADO'
        pago_reg.save()
    else:  # PENDING
        pago_reg.estado = 'PENDIENTE'
        pago_reg.save()

    return HttpResponse(status=200)


# ──────────────────────────────────────────────────────────────────────────
# ENDPOINT 4: Página de éxito (redirección informativa desde el Widget)
# ──────────────────────────────────────────────────────────────────────────

@require_GET
def pago_exitoso(request):
    """
    GET /pagos/exito/?id=<transaction_id>

    Wompi redirige aquí tras el Web Checkout (redirect-url). Según la doc oficial,
    la redirección NO debe usarse como método de validación de la transacción —
    solo con fines informativos para el usuario. La fuente de verdad real y
    definitiva sigue siendo `wompi_webhook`, que es idempotente.

    Aun así, consultamos la API de Wompi aquí mismo para darle al usuario feedback
    inmediato (en vez de dejarlo esperando a que llegue el webhook, que puede
    tardar unos segundos). Si el webhook ya corrió antes de que el usuario vuelva,
    esto simplemente no hace nada nuevo (_completar_compra_si_aprobado es idempotente).
    """
    transaction_id = request.GET.get('id', '')
    pago = None
    estado_mostrado = 'DESCONOCIDO'

    if transaction_id:
        pago = PagoWompi.objects.filter(wompi_transaction_id=transaction_id).first()

        if not pago:
            # El webhook probablemente no ha llegado todavía — consultamos directo a Wompi.
            try:
                tx = wompi.consultar_transaccion(transaction_id)
            except wompi.WompiError:
                logger.exception('pago_exitoso: no se pudo consultar la transacción en Wompi')
                tx = None

            if tx:
                referencia = tx.get('reference')
                pago = PagoWompi.objects.filter(referencia=referencia).first()

                if pago:
                    pago.wompi_transaction_id = tx.get('id', transaction_id)
                    pago.payment_method_type  = tx.get('payment_method_type', '')
                    pago.estado_wompi_raw     = tx.get('status')
                    pago.metadata_json        = json.dumps(tx)[:9000]

                    estado_wompi = tx.get('status')
                    if estado_wompi == 'APPROVED':
                        pago.save()
                        try:
                            pago = _completar_compra_si_aprobado(pago, tx)
                        except ValueError:
                            logger.exception('pago_exitoso: no se pudo completar la compra')
                    elif estado_wompi in ('DECLINED', 'ERROR'):
                        pago.estado        = 'FALLIDO'
                        pago.failed_at     = timezone.now()
                        pago.error_message = tx.get('status_message', '')
                        pago.save()
                    elif estado_wompi == 'VOIDED':
                        pago.estado = 'CANCELADO'
                        pago.save()
                    else:
                        pago.estado = 'PENDIENTE'  # ej. PSE aún procesando
                        pago.save()

        if pago:
            estado_mostrado = pago.estado

    return render(request, 'pagos/pago_exitoso.html', {
        'pago':           pago,
        'transaction_id': transaction_id,
        'reference':      pago.referencia if pago else '',
        'status':         pago.estado_wompi_raw if pago else estado_mostrado,
        'estado':         estado_mostrado,
        'carrito_cantidad': 0,
    })