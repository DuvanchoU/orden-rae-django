import json
import logging
import stripe

from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required

from .models import PagoStripe

logger = logging.getLogger(__name__)

stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────

def _get_cliente(request):
    """
    Retorna la instancia de Clientes (ventas.models) correspondiente al usuario.
    El modelo de autenticación es ventas.Clientes (tiene id_cliente, email, etc.).
    Si el usuario autenticado es directamente una instancia de Clientes, se retorna.
    En caso contrario busca por email.
    """
    from ventas.models import Clientes
    if not request.user.is_authenticated:
        return None

    # Si el modelo de usuario ES Clientes (AUTH_USER_MODEL = 'ventas.Clientes')
    if isinstance(request.user, Clientes):
        return request.user

    # Fallback: buscar por email (cuando AUTH_USER_MODEL es distinto)
    return Clientes.objects.filter(
        email=request.user.email, deleted_at__isnull=True
    ).first()


def _get_carrito_items(request):
    from ventas.models import Carritos, ItemsCarrito
    from inventario.models import Producto

    carrito_bd = None
    if request.user.is_authenticated:
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


def _calcular_totales(items_data, cupon=None):
    # Q garantiza exactamente 2 decimales en cada paso para que
    # Django DecimalField(decimal_places=2) no lance ValidationError.
    Q = Decimal('0.01')

    subtotal  = sum(
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

    # FIX: cuantizar el total final — la suma puede generar precisión
    # interna extra en Python que Django rechaza en DecimalField(decimal_places=2)
    total = (subtotal + impuesto - descuento).quantize(Q, rounding=ROUND_HALF_UP)

    return {
        'subtotal':  subtotal,
        'impuesto':  impuesto,
        'descuento': descuento,
        'total':     total,
    }


def _cop_a_stripe_amount(monto_cop: Decimal) -> int:
    """
    COP (Peso colombiano) es ZERO-DECIMAL en Stripe.
    https://stripe.com/docs/currencies#zero-decimal

    Se envía el valor en pesos directamente, SIN multiplicar por 100.
    Ej: $50.000 COP  →  amount=50000
    """
    return int(monto_cop.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


# ──────────────────────────────────────────────────────────────────────────
# DEBUG — solo con DEBUG=True
# ──────────────────────────────────────────────────────────────────────────

@require_GET
def debug_stripe(request):
    """GET /pagos/debug-stripe/  — verifica configuración. Solo en DEBUG=True."""
    if not getattr(settings, 'DEBUG', False):
        return HttpResponse('No disponible en producción', status=403)

    pk = getattr(settings, 'STRIPE_PUBLIC_KEY', '')
    sk = getattr(settings, 'STRIPE_SECRET_KEY', '')
    wh = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')

    api_ok = False
    api_err = ''
    try:
        stripe.PaymentIntent.list(limit=1)
        api_ok = True
    except stripe.error.AuthenticationError as e:
        api_err = f'Clave secreta inválida: {e}'
    except Exception as e:
        api_err = str(e)

    return JsonResponse({
        'STRIPE_PUBLIC_KEY':      f'{pk[:15]}…' if pk else '❌ NO CONFIGURADA',
        'STRIPE_SECRET_KEY':      f'{sk[:15]}…' if sk else '❌ NO CONFIGURADA',
        'STRIPE_WEBHOOK_SECRET':  f'{wh[:15]}…' if wh else '⚠️ No configurada',
        'pk_es_test':             pk.startswith('pk_test_') if pk else False,
        'sk_es_test':             sk.startswith('sk_test_') if sk else False,
        'api_conecta_ok':         api_ok,
        'api_error':              api_err,
        'stripe_lib_version':     stripe.VERSION,
    })


# ──────────────────────────────────────────────────────────────────────────
# ENDPOINT 1: Crear PaymentIntent
# ──────────────────────────────────────────────────────────────────────────

@require_POST
@login_required
def crear_payment_intent(request):
    """POST /pagos/crear-payment-intent/"""
    if not stripe.api_key:
        logger.error('STRIPE_SECRET_KEY no configurada')
        return JsonResponse(
            {'error': 'Pasarela de pago no configurada. Contacta al administrador.'},
            status=500
        )

    try:
        body  = json.loads(request.body or '{}')
        cupon = body.get('cupon') or request.session.get('cupon_activo')

        items = _get_carrito_items(request)
        if not items:
            return JsonResponse({'error': 'El carrito está vacío'}, status=400)

        totales       = _calcular_totales(items, cupon)
        amount_stripe = _cop_a_stripe_amount(totales['total'])

        # Mínimo Stripe para COP zero-decimal: 500 pesos
        if amount_stripe < 500:
            return JsonResponse(
                {'error': f'Monto mínimo: $500 COP (actual: ${amount_stripe})'},
                status=400
            )

        cliente = _get_cliente(request)
        if not cliente:
            return JsonResponse({'error': 'No se encontró el perfil de cliente.'}, status=404)

        desc = ', '.join(
            f"{i['producto'].referencia_producto or i['producto'].codigo_producto} x{i['cantidad']}"
            for i in items[:5]
        )

        logger.info(f'Creando PI: amount={amount_stripe} COP para {getattr(cliente, "email", "anon")}')

        intent = stripe.PaymentIntent.create(
            amount=amount_stripe,
            currency='cop',
            payment_method_types=['card'],
            description=f'ORDER RAE — {desc}',
            metadata={
                'cliente_id':    str(cliente.id_cliente) if cliente else '',
                'cliente_email': cliente.email           if cliente else '',
                'session_key':   request.session.session_key or '',
                'descuento':     str(totales['descuento']),
                'cupon_codigo':  cupon.get('codigo', '') if cupon else '',
            },
        )

        PagoStripe.objects.create(
            payment_intent_id=intent.id,
            cliente_id=cliente.id_cliente if cliente else None,
            # BUG FIX: guardamos en pesos (zero-decimal), igual que lo que enviamos a Stripe
            monto=amount_stripe,
            moneda='cop',
            estado='PENDIENTE',
            descripcion=desc,
        )

        logger.info(f'PaymentIntent creado: {intent.id}')

        return JsonResponse({
            'client_secret':     intent.client_secret,
            'payment_intent_id': intent.id,
            'total':             float(totales['total']),
            'subtotal':          float(totales['subtotal']),
            'impuesto':          float(totales['impuesto']),
            'descuento':         float(totales['descuento']),
            'amount_stripe':     amount_stripe,
        })

    except stripe.error.AuthenticationError:
        logger.error('Stripe AuthenticationError — verifica STRIPE_SECRET_KEY')
        return JsonResponse(
            {'error': 'Error de autenticación con el proveedor de pagos.'},
            status=500
        )
    except stripe.error.StripeError as e:
        logger.error(f'StripeError en crear_payment_intent: {e}')
        return JsonResponse(
            {'error': str(getattr(e, 'user_message', None) or e)},
            status=400
        )
    except Exception as e:
        logger.exception('Error inesperado en crear_payment_intent')
        return JsonResponse({'error': str(e)}, status=500)


# ──────────────────────────────────────────────────────────────────────────
# ENDPOINT 2: Confirmar Pago → crea Pedido + Venta
# ──────────────────────────────────────────────────────────────────────────

@require_POST
@login_required
def confirmar_pago(request):
    """POST /pagos/confirmar-pago/"""
    from ventas.models import (
        Clientes, Ventas, DetalleVenta, MetodosPago,
        Pedido, DetallePedido, Carritos, ItemsCarrito,
    )

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Datos JSON inválidos'}, status=400)

    payment_intent_id = data.get('payment_intent_id', '').strip()
    if not payment_intent_id:
        return JsonResponse({'error': 'payment_intent_id es requerido'}, status=400)

    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        logger.info(f'PI {payment_intent_id} → estado: {intent.status}')

        if intent.status != 'succeeded':
            return JsonResponse(
                {'error': f'Pago no completado (estado: {intent.status})'},
                status=400
            )

        # Idempotencia: si ya fue procesado, retornar éxito sin duplicar
        pago_reg = PagoStripe.objects.filter(payment_intent_id=payment_intent_id).first()
        if pago_reg and pago_reg.estado == 'COMPLETADO' and pago_reg.venta_id:
            return JsonResponse({
                'success':       True,
                'order_number':  f"FAC-{pago_reg.venta_id:06d}",
                'pedido_number': f"PED-{pago_reg.pedido_id:06d}" if pago_reg.pedido_id else '',
                # BUG FIX: monto ya está en pesos (zero-decimal), no dividir entre 100
                'total':         float(pago_reg.monto),
                'message':       'Pago ya procesado anteriormente',
            })

        cliente = _get_cliente(request)
        if not cliente:
            return JsonResponse({'error': 'Cliente no encontrado'}, status=404)

        items = _get_carrito_items(request)
        if not items:
            return JsonResponse({'error': 'Carrito vacío'}, status=400)

        cupon   = request.session.get('cupon_activo')
        totales = _calcular_totales(items, cupon)

        envio    = data.get('envio',    {})
        contacto = data.get('contacto', {})

        dirs            = [envio.get('ciudad',''), envio.get('direccion',''), envio.get('apartamento','')]
        direccion_envio = ' - '.join(d.strip() for d in dirs if d.strip())
        observaciones   = (
            f"Pedido web | Stripe PI: {payment_intent_id[:20]} | "
            f"{contacto.get('nombre','')} {contacto.get('telefono','')} | "
            f"{direccion_envio}"
        )
        instrucciones = envio.get('instrucciones', '').strip()
        if instrucciones:
            observaciones += f" | {instrucciones}"

        ahora         = timezone.now()
        fecha_entrega = (ahora + timezone.timedelta(days=5)).date()

        metodo_pago, _ = MetodosPago.objects.get_or_create(
            nombre='Stripe — Tarjeta',
            defaults={
                'descripcion': 'Pago con tarjeta vía Stripe',
                'created_at':  ahora,
                'updated_at':  ahora,
            }
        )

        carrito_bd = None
        if hasattr(cliente, 'id_cliente'):
            carrito_bd = Carritos.objects.filter(cliente=cliente, deleted_at__isnull=True).first()
        if not carrito_bd and request.session.session_key:
            carrito_bd = Carritos.objects.filter(
                session_id=request.session.session_key, deleted_at__isnull=True
            ).first()

        with transaction.atomic():
            from usuarios.models import Usuarios
            # usuario_id es NOT NULL en pedido y ventas.
            # Usamos el usuario "sistema" (id=1) para pedidos web.
            # Si el admin tiene una cuenta en Usuarios, cámbialo por su id.
            usuario_sistema = Usuarios.objects.filter(pk=1).first()

            # ── Número de Pedido ──────────────────────────────────────────
            ult_p  = Pedido.objects.filter(deleted_at__isnull=True).order_by('-id_pedido').first()
            cp     = (ult_p.id_pedido if ult_p else 0) + 1
            num_p  = f"PED-{cp:06d}"
            while Pedido.objects.filter(numero_pedido=num_p).exists():
                cp += 1
                num_p = f"PED-{cp:06d}"

            # BUG FIX: estado_pedido ENUM real = 'PENDIENTE'|'EN PROCESO'|'ENTREGADO'|'CANCELADO'
            # 'CONFIRMADO' no existe en la BD → Data truncated error.
            # BUG FIX: usuario es NOT NULL en la tabla → usar usuario_sistema.
            pedido = Pedido(
                cliente=cliente,
                usuario=usuario_sistema,
                asesor=None,
                fecha_pedido=ahora,
                fecha_entrega_estimada=fecha_entrega,
                total_pedido=totales['total'],
                estado_pedido='PENDIENTE',        # ← valor válido en el ENUM
                estado_facturacion='NO_FACTURADO',
                direccion_entrega=direccion_envio,
                numero_pedido=num_p,
                created_at=ahora,
                updated_at=ahora,
            )
            pedido.save()

            for item in items:
                sub = (item['precio_unitario'] * item['cantidad']).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
                DetallePedido(
                    pedido=pedido,
                    producto=item['producto'],
                    cantidad=item['cantidad'],
                    precio_unitario=item['precio_unitario'],
                    subtotal=sub,
                    created_at=ahora,
                    updated_at=ahora,
                ).save()

            # ── Número de Factura ─────────────────────────────────────────
            ult_v  = Ventas.objects.filter(prefijo='FAC', deleted_at__isnull=True).order_by('-id_venta').first()
            cv     = (ult_v.id_venta if ult_v else 0) + 1
            num_f  = f"FAC-{cv:06d}"
            while Ventas.objects.filter(numero_factura=num_f).exists():
                cv += 1
                num_f = f"FAC-{cv:06d}"

            # BUG FIX: usuario es NOT NULL en ventas → usar usuario_sistema.
            # BUG FIX: estado_venta ENUM real = 'COMPLETADA'|'CANCELADA'|'PENDIENTE'
            venta = Ventas(
                usuario=usuario_sistema,
                cliente=cliente,
                pedido=pedido,
                tipo_venta='DIRECTA',
                fecha_venta=ahora,
                subtotal=totales['subtotal'],
                impuesto=totales['impuesto'],
                descuento=totales['descuento'],
                total=totales['total'],
                estado_venta='PENDIENTE',          # ← valor válido en el ENUM
                metodo_pago=metodo_pago,
                observaciones=observaciones,
                numero_factura=num_f,
                prefijo='FAC',
                created_at=ahora,
                updated_at=ahora,
            )
            venta.save()

            for item in items:
                sub = (item['precio_unitario'] * item['cantidad']).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
                DetalleVenta(
                    venta=venta,
                    producto=item['producto'],
                    cantidad=item['cantidad'],
                    precio_unitario=item['precio_unitario'],
                    descuento=Decimal('0.00'),
                    subtotal=sub,
                    costo_estimado=None,
                    created_at=ahora,
                    updated_at=ahora,
                ).save()

            # ── Actualizar registro de pago ───────────────────────────────
            if pago_reg:
                pago_reg.estado      = 'COMPLETADO'
                pago_reg.venta_id    = venta.id_venta
                pago_reg.pedido_id   = pedido.id_pedido
                pago_reg.confirmed_at = ahora
                pago_reg.save()
            else:
                PagoStripe.objects.filter(payment_intent_id=payment_intent_id).update(
                    estado='COMPLETADO',
                    venta_id=venta.id_venta,
                    pedido_id=pedido.id_pedido,
                    confirmed_at=ahora,
                )

            # BUG FIX: verificar que el cliente tenga el campo 'direccion' antes de usarlo
            if direccion_envio and not getattr(cliente, 'direccion', None):
                Clientes.objects.filter(pk=cliente.pk).update(
                    direccion=direccion_envio, updated_at=ahora
                )

            # ── Vaciar carrito ────────────────────────────────────────────
            if carrito_bd:
                ItemsCarrito.objects.filter(carrito=carrito_bd).delete()
                Carritos.objects.filter(pk=carrito_bd.pk).update(
                    deleted_at=ahora, updated_at=ahora
                )

            request.session['carrito']          = {}
            request.session['carrito_cantidad'] = 0
            request.session.pop('cupon_activo', None)
            request.session.modified = True

        logger.info(f'Compra OK: {venta.numero_factura} / {pedido.numero_pedido}')

        return JsonResponse({
            'success':       True,
            'order_number':  venta.numero_factura,
            'pedido_number': pedido.numero_pedido,
            'total':         float(totales['total']),
            'subtotal':      float(totales['subtotal']),
            'impuesto':      float(totales['impuesto']),
            'descuento':     float(totales['descuento']),
            'items':         len(items),
            'message':       '¡Pedido creado exitosamente!',
        })

    except stripe.error.AuthenticationError:
        return JsonResponse({'error': 'Error de autenticación con Stripe'}, status=500)
    except stripe.error.StripeError as e:
        logger.error(f'StripeError en confirmar_pago: {e}')
        return JsonResponse({'error': str(getattr(e, 'user_message', None) or e)}, status=400)
    except Exception as e:
        logger.exception('Error inesperado en confirmar_pago')
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


# ──────────────────────────────────────────────────────────────────────────
# ENDPOINT 3: Webhook
# ──────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload        = request.body
    sig_header     = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')

    if webhook_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except ValueError:
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            return HttpResponse(status=400)
    else:
        # Desarrollo sin webhook secret: procesar sin verificar firma
        logger.warning('Webhook sin verificación de firma (STRIPE_WEBHOOK_SECRET no configurado)')
        try:
            event = json.loads(payload)
        except Exception:
            return HttpResponse(status=400)

    event_type = event['type']
    data_obj   = event['data']['object']
    logger.info(f'Webhook Stripe: {event_type}')

    if event_type == 'payment_intent.succeeded':
        pi_id = data_obj['id']
        PagoStripe.objects.filter(payment_intent_id=pi_id, estado='PENDIENTE').update(
            estado='COMPLETADO', confirmed_at=timezone.now()
        )
    elif event_type == 'payment_intent.payment_failed':
        pi_id = data_obj['id']
        err   = data_obj.get('last_payment_error', {})
        PagoStripe.objects.filter(payment_intent_id=pi_id).update(
            estado='FALLIDO', failed_at=timezone.now(),
            error_code=err.get('code', ''), error_message=err.get('message', ''),
        )
    elif event_type == 'charge.refunded':
        pi_id = data_obj.get('payment_intent', '')
        if pi_id:
            PagoStripe.objects.filter(payment_intent_id=pi_id).update(
                estado='REEMBOLSADO',
                monto_reembolsado=data_obj.get('amount_refunded', 0),
            )

    return HttpResponse(status=200)


# ──────────────────────────────────────────────────────────────────────────
# ENDPOINT 4: Página éxito
# ──────────────────────────────────────────────────────────────────────────

@require_GET
def pago_exitoso(request):
    payment_intent_id = request.GET.get('payment_intent', '')
    pago = PagoStripe.objects.filter(
        payment_intent_id=payment_intent_id
    ).first() if payment_intent_id else None

    return render(request, 'pagos/exito.html', {
        'pago':              pago,
        'payment_intent_id': payment_intent_id,
        'carrito_cantidad':  0,
    })