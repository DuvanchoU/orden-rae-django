from django.db import models
from django.utils import timezone


class PagoWompi(models.Model):
    """
    Registra cada intento de pago procesado a través de Wompi.
    Se vincula a la Venta y al Pedido una vez confirmado.

    """
    ESTADOS = [
        ('PENDIENTE',   'Pendiente'),
        ('COMPLETADO',  'Completado'),    # Wompi: APPROVED
        ('FALLIDO',     'Fallido'),       # Wompi: DECLINED / ERROR
        ('CANCELADO',   'Cancelado'),     # Wompi: VOIDED
        ('REEMBOLSADO', 'Reembolsado'),
    ]

    # Identificadores Wompi
    referencia           = models.CharField(max_length=100, unique=True, db_index=True)
    wompi_transaction_id = models.CharField(max_length=100, blank=True, null=True, unique=True, db_index=True)
    payment_method_type  = models.CharField(max_length=30, blank=True, null=True)  # CARD, PSE, NEQUI, etc.

    # Relaciones internas (opcionales hasta confirmar el pago)
    venta_id   = models.IntegerField(blank=True, null=True)
    pedido_id  = models.IntegerField(blank=True, null=True)
    cliente_id = models.IntegerField(blank=True, null=True)

    monto              = models.BigIntegerField(help_text='Monto en pesos COP (para mostrar en UI)')
    monto_centavos     = models.BigIntegerField(help_text='amount_in_cents — el valor real que maneja Wompi')
    monto_reembolsado  = models.BigIntegerField(default=0)
    moneda             = models.CharField(max_length=3, default='COP')

    estado           = models.CharField(max_length=12, choices=ESTADOS, default='PENDIENTE', db_index=True)
    estado_wompi_raw = models.CharField(max_length=20, blank=True, null=True,
                                        help_text='Último status crudo de Wompi: APPROVED/DECLINED/ERROR/PENDING/VOIDED')
    descripcion       = models.TextField(blank=True, null=True)
    metadata_json     = models.TextField(blank=True, null=True, help_text='Última respuesta cruda de Wompi (auditoría)')

    # Datos de contacto/envío capturados ANTES de abrir el Widget, para poder
    # crear el Pedido/Venta tanto si confirma el frontend como si solo llega el webhook.
    checkout_data_json = models.TextField(blank=True, null=True)

    created_at   = models.DateTimeField(default=timezone.now)
    updated_at   = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    failed_at    = models.DateTimeField(blank=True, null=True)

    error_code    = models.CharField(max_length=100, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'pagos_wompi'
        ordering = ['-created_at']

    def monto_formateado(self):
        return f"${int(self.monto):,}".replace(',', '.')

    def __str__(self):
        return f"Pago {self.referencia} | {self.estado} | {self.monto_formateado()}"