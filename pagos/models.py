from django.db import models
from django.utils import timezone


class PagoStripe(models.Model):
    """
    Registra cada intento de pago con Stripe.
    Se vincula a la Venta y al Pedido una vez confirmado.

    IMPORTANTE — COP es moneda zero-decimal en Stripe:
    El campo `monto` almacena pesos colombianos directamente (ej. 50000 = $50.000 COP).
    NO se multiplica ni divide por 100 en ningún punto del flujo.
    Ref: https://stripe.com/docs/currencies#zero-decimal
    """
    ESTADOS = [
        ('PENDIENTE',   'Pendiente'),
        ('COMPLETADO',  'Completado'),
        ('FALLIDO',     'Fallido'),
        ('CANCELADO',   'Cancelado'),
        ('REEMBOLSADO', 'Reembolsado'),
    ]

    # Stripe identifiers
    payment_intent_id   = models.CharField(max_length=255, unique=True, db_index=True)
    payment_method_id   = models.CharField(max_length=255, blank=True, null=True)
    checkout_session_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)

    # Relaciones internas (opcionales hasta confirmar el pago)
    venta_id   = models.IntegerField(blank=True, null=True)
    pedido_id  = models.IntegerField(blank=True, null=True)
    cliente_id = models.IntegerField(blank=True, null=True)

    # Monto en PESOS COP (zero-decimal: Stripe recibe el mismo valor entero)
    monto             = models.BigIntegerField(
        help_text='Monto en pesos COP — igual al amount enviado a Stripe (zero-decimal)'
    )
    monto_reembolsado = models.BigIntegerField(default=0)
    moneda            = models.CharField(max_length=3, default='cop')

    estado      = models.CharField(max_length=12, choices=ESTADOS, default='PENDIENTE', db_index=True)
    descripcion = models.TextField(blank=True, null=True)
    metadata_json = models.TextField(blank=True, null=True, help_text='JSON extra enviado a Stripe')

    # Timestamps
    created_at   = models.DateTimeField(default=timezone.now)
    updated_at   = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    failed_at    = models.DateTimeField(blank=True, null=True)

    # Error info
    error_code    = models.CharField(max_length=100, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'pagos_stripe'
        ordering = ['-created_at']

    def monto_cop(self):
        """
        Retorna el monto en COP.
        COP es zero-decimal → el valor guardado ya está en pesos; NO dividir entre 100.
        """
        return self.monto  # BUG FIX: era self.monto / 100, incorrecto para zero-decimal

    def monto_formateado(self):
        return f"${int(self.monto_cop()):,}".replace(',', '.')

    def __str__(self):
        return f"Pago {self.payment_intent_id[:20]}… | {self.estado} | {self.monto_formateado()}"