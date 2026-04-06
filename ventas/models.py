from decimal import Decimal

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum
from django.db import transaction
from datetime import timedelta
import re

class Clientes(models.Model):
    ESTADOS_CLIENTE = [
        ('ACTIVO', 'Activo'),
        ('INACTIVO', 'Inactivo'),
    ]

    GENEROS = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('O', 'Otro'),
    ]

    foto_perfil = models.ImageField(
        upload_to='avatars/', 
        null=True, 
        blank=True, 
        default='avatars/default-avatar-1.png'
    )
    id_cliente = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100, blank=True, null=True)
    documento = models.CharField(max_length=50, null=True, blank=True)
    genero = models.CharField(max_length=1, choices=GENEROS, blank=True, null=True)
    contrasena_cliente = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    fecha_registro = models.DateTimeField(blank=True, null=True)
    estado = models.CharField(
        max_length=8, 
        choices=ESTADOS_CLIENTE,
        default='ACTIVO',
        blank=True, 
        null=True
    )
    last_login = models.DateTimeField(blank=True, null=True)
    ultimo_login = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        managed = True
        db_table = 'clientes'
        ordering = ['apellido', 'nombre']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['telefono']),
            models.Index(fields=['documento']),
            models.Index(fields=['estado']),
        ]
    
    def __str__(self):
        if self.apellido:
            return f"{self.nombre} {self.apellido}"
        return self.nombre

    def clean(self):
        """Validaciones del modelo"""
        # Validar nombre
        if not self.nombre or not self.nombre.strip():
            raise ValidationError("El nombre es obligatorio")
        
        if len(self.nombre.strip()) < 2:
            raise ValidationError("El nombre debe tener al menos 2 caracteres")
        
        # Validar documento si existe
        if self.documento:
            self.documento = self.documento.strip()
            if len(self.documento) < 5:
                raise ValidationError("El documento debe tener al menos 5 caracteres")
            
            # Validar que solo sean números
            doc_limpio = re.sub(r'[^\d]', '', self.documento)
            if not doc_limpio:
                raise ValidationError("El documento solo debe contener números")
            
            # Validar unicidad
            clientes_con_doc = Clientes.objects.filter(
                documento=self.documento,
                deleted_at__isnull=True
            )
            if self.pk:
                clientes_con_doc = clientes_con_doc.exclude(pk=self.pk)
            if clientes_con_doc.exists():
                raise ValidationError(f"El documento '{self.documento}' ya está registrado")
        
        # Validar email si existe
        if self.email:
            self.email = self.email.lower().strip()
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, self.email):
                raise ValidationError("El email no es válido")
            
            # Validar email único (excluyendo soft deletes y sí mismo)
            clientes_con_email = Clientes.objects.filter(
                email=self.email,
                deleted_at__isnull=True
            )
            if self.pk:
                clientes_con_email = clientes_con_email.exclude(pk=self.pk)
            
            if clientes_con_email.exists():
                raise ValidationError(f"El email '{self.email}' ya está registrado")
        
        # Validar teléfono si existe
        if self.telefono:
            self.telefono = self.telefono.strip()
            # Eliminar espacios y caracteres no numéricos excepto +
            telefono_limpio = re.sub(r'[^\d+]', '', self.telefono)
            if len(telefono_limpio) < 7:
                raise ValidationError("El teléfono debe tener al menos 7 dígitos")
            if len(telefono_limpio) > 15:
                raise ValidationError("El teléfono no puede tener más de 15 dígitos")
        
        # Validar dirección
        if self.direccion and len(self.direccion.strip()) < 5:
            raise ValidationError("La dirección debe tener al menos 5 caracteres")

    def save(self, *args, **kwargs):
        """Auto-gestión de timestamps"""
        if not self.pk and not self.created_at:
            self.created_at = timezone.now()
            if not self.fecha_registro:
                self.fecha_registro = timezone.now()
        
        self.updated_at = timezone.now()
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """Soft delete"""
        self.deleted_at = timezone.now()
        self.estado = 'INACTIVO'
        self.save()
        return self

    def hard_delete(self):
        """Eliminación física real (solo si no tiene relaciones)"""
        if self.tiene_pedidos_asociados():
            raise ValidationError("No se puede eliminar permanentemente un cliente con pedidos asociados")
        super().delete()

    def restore(self):
        """Restaurar cliente eliminado"""
        self.deleted_at = None
        self.estado = 'ACTIVO'
        self.save()

    def esta_activo(self):
        """Verifica si el cliente está activo"""
        return self.estado == 'ACTIVO' and self.deleted_at is None

    def activar(self):
        """Activar cliente"""
        self.estado = 'ACTIVO'
        self.deleted_at = None
        self.save()

    def desactivar(self):
        """Desactivar cliente (soft delete)"""
        if self.tiene_pedidos_pendientes():
            raise ValidationError("No se puede desactivar un cliente con pedidos pendientes")
        self.estado = 'INACTIVO'
        self.save()

    def get_nombre_completo(self):
        """Obtiene el nombre completo formateado"""
        if self.apellido:
            return f"{self.nombre} {self.apellido}".strip()
        return self.nombre.strip()

    def tiene_pedidos_asociados(self):
        """Verifica si tiene pedidos (incluyendo eliminados)"""
        from ventas.models import Pedido
        return Pedido.objects.filter(cliente=self).exists()

    def tiene_pedidos_activos(self):
        """Verifica si tiene pedidos activos"""
        from ventas.models import Pedido
        return Pedido.objects.filter(
            cliente=self,
            deleted_at__isnull=True,
            estado_pedido__in=['PENDIENTE', 'EN_PROCESO']
        ).exists()

    def tiene_pedidos_pendientes(self):
        """Verifica si tiene pedidos pendientes de pago"""
        from ventas.models import Pedido
        return Pedido.objects.filter(
            cliente=self,
            deleted_at__isnull=True,
            estado_pago='PENDIENTE'
        ).exists()

    def get_total_pedidos(self):
        """Obtiene el total gastado por el cliente"""
        from ventas.models import Pedido
        total = Pedido.objects.filter(
            cliente=self,
            deleted_at__isnull=True,
            estado_pedido='COMPLETADO'
        ).aggregate(total=Sum('total'))['total'] or 0
        return float(total)

    def get_cantidad_pedidos(self):
        """Obtiene la cantidad de pedidos del cliente"""
        from ventas.models import Pedido
        return Pedido.objects.filter(
            cliente=self,
            deleted_at__isnull=True
        ).count()

    def puede_eliminarse(self):
        """Verifica si se puede eliminar (soft delete)"""
        return not self.tiene_pedidos_activos()

    def get_info_contacto(self):
        """Retorna información de contacto formateada"""
        info = {
            'nombre': self.get_nombre_completo(),
            'email': self.email or 'No registrado',
            'telefono': self.telefono or 'No registrado',
            'direccion': self.direccion or 'No registrada',
            'documento': self.documento or 'No registrado',
        }
        return info

    def __str__(self):
        estado_icon = "✓" if self.esta_activo() else "✗"
        return f"{estado_icon} {self.get_nombre_completo()} ({self.email or 'Sin email'})"
    
    # =====================================================================
    # MÉTODOS DE COMPATIBILIDAD CON DJANGO AUTH
    # =====================================================================
    
    @property
    def is_authenticated(self):
        return self.esta_activo()
    
    @property
    def is_anonymous(self):
        return False
    
    @property
    def is_active(self):
        return self.estado == 'ACTIVO' and self.deleted_at is None
    
    @property
    def username(self):
        return self.email or f"cliente_{self.id_cliente}"
    
    def get_full_name(self):
        if self.apellido:
            return f"{self.nombre} {self.apellido}".strip()
        return self.nombre.strip()
    
    def get_short_name(self):
        return self.nombre

class MetodosPago(models.Model):
    id_metodo = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'metodos_pago'

    def __str__(self):
            return self.nombre


class Carritos(models.Model):
    id_carrito = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(Clientes, models.DO_NOTHING, blank=True, null=True)
    session_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'carritos'

    def __str__(self):
        if self.cliente:
            return f"Carrito #{self.id_carrito} - {self.cliente}"
        return f"Carrito #{self.id_carrito} (Sin cliente)"
    

class ItemsCarrito(models.Model):
    id_item = models.AutoField(primary_key=True)
    carrito = models.ForeignKey(Carritos, models.DO_NOTHING, related_name='items')
    producto = models.ForeignKey('inventario.Producto', models.DO_NOTHING) 
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'items_carrito'

    def __str__(self):
        return f"{self.producto} x{self.cantidad}"

# ============================================================================
# COTIZACIONES
# ============================================================================
class Cotizaciones(models.Model):
    ESTADOS_COTIZACION = [
        ('borrador', 'Borrador'),
        ('enviada', 'Enviada'),
        ('aceptada', 'Aceptada'),
        ('rechazada', 'Rechazada'),
        ('vencida', 'Vencida'),
        ('cancelada', 'Cancelada'),
    ]

    id_cotizacion = models.AutoField(primary_key=True)
    numero_cotizacion = models.CharField(unique=True, max_length=255)
    cliente = models.ForeignKey(Clientes, models.DO_NOTHING)
    usuario = models.ForeignKey('usuarios.Usuarios', models.DO_NOTHING, blank=True, null=True)
    venta_id = models.IntegerField(blank=True, null=True)
    fecha_cotizacion = models.DateField(blank=True, null=True)
    fecha_vencimiento = models.DateField()
    estado = models.CharField(
        max_length=10,
        choices=ESTADOS_COTIZACION,
        default='borrador'
    )
    tiempo_entrega = models.CharField(max_length=255, blank=True, null=True)
    validez_dias = models.IntegerField(blank=True, default=30)
    moneda = models.CharField(max_length=10, blank=True, default='COP')
    requiere_produccion = models.IntegerField(default=False)
    observaciones = models.TextField(blank=True, null=True)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    impuesto = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    consecutivo = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'cotizaciones'
        ordering = ['-fecha_cotizacion', '-created_at']
        indexes = [
            models.Index(fields=['numero_cotizacion']),
            models.Index(fields=['estado']),
            models.Index(fields=['cliente']),
        ]

    def __str__(self):
        return f"Cotización #{self.numero_cotizacion} - {self.cliente}"
    
    def subtotal_formateado(self):
        """
        Retorna el subtotal formateado sin decimales y con separador de miles
        Ejemplo: 1199998 → $1.199.998
        """
        return f"{int(self.subtotal):,}".replace(",", ".")
    
    def impuesto_formateado(self):
        """
        Retorna el impuesto formateado sin decimales y con separador de miles
        Ejemplo: 228000 → $228.000
        """
        return f"{int(self.impuesto):,}".replace(",", ".")
    
    def descuento_formateado(self):
        """
        Retorna el descuento formateado sin decimales y con separador de miles
        Ejemplo: 50000 → $50.000
        """
        if self.descuento:
            return f"{int(self.descuento):,}".replace(",", ".")
        return "0"
    
    def total_formateado(self):
        """
        Retorna el total formateado sin decimales y con separador de miles
        Ejemplo: 1427998 → $1.427.998
        """
        return f"{int(self.total):,}".replace(",", ".")
    
    def clean(self):
        """Validaciones del modelo"""
        # Validar fechas
        if self.fecha_cotizacion and self.fecha_vencimiento:
            if self.fecha_vencimiento < self.fecha_cotizacion:
                raise ValidationError("La fecha de vencimiento no puede ser anterior a la fecha de cotización")
        
        # Validar montos
        if self.subtotal < 0:
            raise ValidationError("El subtotal no puede ser negativo")
        if self.impuesto < 0:
            raise ValidationError("El impuesto no puede ser negativo")
        if self.descuento < 0:
            raise ValidationError("El descuento no puede ser negativo")
        if self.total < 0:
            raise ValidationError("El total no puede ser negativo")
        
        # Validar que total sea consistente
        total_calculado = self.subtotal + self.impuesto - self.descuento
        if abs(float(self.total) - float(total_calculado)) > 0.01:
            raise ValidationError(f"El total debe ser subtotal + impuesto - descuento ({total_calculado})")

    def save(self, *args, **kwargs):
        """Auto-gestión de timestamps y número de cotización"""
        if not self.pk and not self.created_at:
            self.created_at = timezone.now()
            if not self.numero_cotizacion:
                # Generar número consecutivo
                ultimo = Cotizaciones.objects.filter(deleted_at__isnull=True).order_by('-consecutivo').first()
                self.consecutivo = (ultimo.consecutivo or 0) + 1
                self.numero_cotizacion = f"COT-{self.consecutivo:06d}"
        
        self.updated_at = timezone.now()

        # Auto-calcular fecha de vencimiento si no existe
        if not self.fecha_vencimiento and self.fecha_cotizacion and self.validez_dias:
            self.fecha_vencimiento = self.fecha_cotizacion + timedelta(days=self.validez_dias)
        
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """Soft delete"""
        self.deleted_at = timezone.now()
        self.save()
        return self

    def hard_delete(self):
        """Eliminación física solo si no tiene venta asociada"""
        if self.venta_id:
            raise ValidationError("No se puede eliminar una cotización que ya fue convertida en venta")
        super().delete()

    def esta_vencida(self):
        """Verifica si la cotización está vencida"""
        if self.fecha_vencimiento:
            return timezone.now().date() > self.fecha_vencimiento
        return False

    def puede_modificarse(self):
        """Solo se puede modificar si está en borrador o enviada"""
        return self.estado in ['borrador', 'enviada']

    def puede_eliminarse(self):
        """Solo se puede eliminar si está en borrador"""
        return self.estado == 'borrador' and not self.venta_id

    def puede_convertirse_en_venta(self):
        """Verifica si puede convertirse en venta"""
        if self.estado != 'aceptada':
            return False, "La cotización debe estar aceptada"
        if self.esta_vencida():
            return False, "La cotización está vencida"
        if self.venta_id:
            return False, "Ya fue convertida en venta"
        return True, ""

    def calcular_totales(self):
        """Calcula subtotal, impuesto, descuento y total desde los detalles"""
        detalles = self.detallecotizacion_set.filter(deleted_at__isnull=True)
        
        subtotal = sum(d.subtotal for d in detalles)
        # Aquí podrías calcular impuesto y descuento según reglas de negocio
        impuesto = subtotal * Decimal('0.19')  # 19% IVA ejemplo
        descuento = self.descuento or 0
        total = subtotal + impuesto - descuento
        
        self.subtotal = subtotal
        self.impuesto = impuesto
        self.total = total
        self.save()

    def convertir_en_venta(self, usuario=None):
        """Convierte la cotización en venta"""
        if not self.puede_convertirse_en_venta()[0]:
            raise ValidationError(self.puede_convertirse_en_venta()[1])
        
        with transaction.atomic():
            # Crear venta
            from .models import Ventas
            venta = Ventas.objects.create(
                usuario=usuario or self.usuario,
                cliente=self.cliente,
                tipo_venta='DESDE_COTIZACION',
                fecha_venta=timezone.now(),
                subtotal=self.subtotal,
                impuesto=self.impuesto,
                descuento=self.descuento,
                total=self.total,
                estado_venta='PENDIENTE',
                observaciones=f"Generada desde cotización {self.numero_cotizacion}"
            )
            
            # Copiar detalles
            for detalle in self.detallecotizacion_set.filter(deleted_at__isnull=True):
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=detalle.producto,
                    cantidad=detalle.cantidad,
                    precio_unitario=detalle.precio_unitario,
                    descuento=detalle.descuento or 0,
                    subtotal=detalle.subtotal,
                    costo_estimado=detalle.costo_estimado
                )
            
            # Actualizar cotización
            self.venta_id = venta.id_venta
            self.estado = 'aceptada'
            self.save()
            
            return venta

    def get_total_formateado(self):
        return f"${int(self.total):,}".replace(",", ".")

    def __str__(self):
        return f"{self.numero_cotizacion} - {self.cliente} ({self.estado})"
    

class DetalleCotizacion(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    cotizacion = models.ForeignKey(Cotizaciones, models.DO_NOTHING)
    producto = models.ForeignKey('inventario.Producto', models.DO_NOTHING)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=15, decimal_places=2)
    descuento = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    costo_estimado = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    observacion = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'detalle_cotizacion'

    def __str__(self):
        return f"{self.producto} x{self.cantidad}"
    
    def precio_unitario_formateado(self):
        """
        Retorna el precio unitario formateado sin decimales y con separador de miles
        """
        return f"{int(self.precio_unitario):,}".replace(",", ".")
    
    def subtotal_formateado(self):
        """
        Retorna el subtotal formateado sin decimales y con separador de miles
        """
        return f"{int(self.subtotal):,}".replace(",", ".")
    
    def descuento_formateado(self):
        """
        Retorna el descuento formateado sin decimales y con separador de miles
        """
        if self.descuento:
            return f"{int(self.descuento):,}".replace(",", ".")
        return "$0"
    
    def clean(self):
        if self.cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor a 0")
        if self.precio_unitario < 0:
            raise ValidationError("El precio unitario no puede ser negativo")
        if self.descuento < 0:
            raise ValidationError("El descuento no puede ser negativo")

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        
        # Calcular subtotal
        self.subtotal = (self.cantidad * self.precio_unitario) - self.descuento
        
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Recalcular totales de la cotización
        if self.cotizacion:
            self.cotizacion.calcular_totales()

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save()
        return self

    def __str__(self):
        return f"{self.producto} x{self.cantidad}"

# ============================================================================
# PEDIDOS
# ============================================================================
class Pedido(models.Model):
    ESTADOS_PEDIDO = [
        ('PENDIENTE', 'Pendiente'),
        ('CONFIRMADO', 'Confirmado'),
        ('EN PROCESO', 'En Proceso'),
        ('COMPLETADO', 'Completado'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    ESTADOS_FACTURACION = [
        ('NO_FACTURADO', 'No Facturado'),
        ('FACTURADO', 'Facturado'),
    ]

    id_pedido = models.AutoField(primary_key=True)
    usuario = models.ForeignKey('usuarios.Usuarios', models.DO_NOTHING, blank=True, null=True)
    cliente = models.ForeignKey('ventas.Clientes', models.DO_NOTHING)
    fecha_pedido = models.DateTimeField(default=timezone.now)
    fecha_entrega_estimada = models.DateField(blank=True, null=True)
    total_pedido = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    estado_pedido = models.CharField(
        max_length=10,
        choices=ESTADOS_PEDIDO,
        default='PENDIENTE'
    )
    direccion_entrega = models.CharField(max_length=255, blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    asesor = models.ForeignKey(
        'usuarios.Usuarios', 
        models.DO_NOTHING, 
        related_name='pedido_asesor_set', 
        blank=True, 
        null=True
    )
    numero_pedido = models.CharField(unique=True, max_length=255, blank=True, null=True)
    foto_orden = models.CharField(max_length=255, blank=True, null=True)
    estado_facturacion = models.CharField(
        max_length=12,
        choices=ESTADOS_FACTURACION,
        default='NO_FACTURADO'
    )
    fecha_facturacion = models.DateTimeField(blank=True, null=True)
    usuario_facturo = models.ForeignKey(
        'usuarios.Usuarios', 
        models.DO_NOTHING, 
        related_name='pedido_usuario_facturo_set', 
        blank=True, 
        null=True
    )

    def precio_formateado(self):
        """
        Retorna el precio formateado sin decimales y con separador de miles
        Ejemplo: 950000 → $950.000
        """
        return f"{int(self.total_pedido):,}".replace(",", ".")
    
    def __str__(self):
        numero = self.numero_pedido or f"#{self.id_pedido}"
        return f"Pedido {numero} - {self.cliente}"
    
    class Meta:
        managed = True
        db_table = 'pedido'
        ordering = ['-fecha_pedido', '-created_at']
        indexes = [
            models.Index(fields=['numero_pedido']),
            models.Index(fields=['estado_pedido']),
            models.Index(fields=['cliente']),
            models.Index(fields=['estado_facturacion']),
        ]

    def clean(self):
        if self.total_pedido < 0:
            raise ValidationError("El total del pedido no puede ser negativo")
        
        if self.fecha_entrega_estimada and self.fecha_pedido:
            if self.fecha_entrega_estimada < self.fecha_pedido.date():
                raise ValidationError("La fecha de entrega no puede ser anterior a la fecha del pedido")

    def save(self, *args, **kwargs):
        if not self.pk and not self.created_at:
            self.created_at = timezone.now()
            if not self.numero_pedido:
                # Generar número de pedido
                ultimo = Pedido.objects.filter(deleted_at__isnull=True).order_by('-id_pedido').first()
                consecutivo = (ultimo.id_pedido or 0) + 1
                self.numero_pedido = f"PED-{consecutivo:06d}"
        
        self.updated_at = timezone.now()
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """Soft delete - solo si está pendiente"""
        if self.estado_pedido not in ['PENDIENTE', 'CANCELADO']:
            raise ValidationError(f"No se puede eliminar un pedido en estado {self.estado_pedido}")
        self.deleted_at = timezone.now()
        self.save()
        return self

    def puede_modificarse(self):
        return self.estado_pedido in ['PENDIENTE', 'CONFIRMADO']

    def puede_eliminarse(self):
        return self.estado_pedido == 'PENDIENTE' and not self.detallepedido_set.filter(deleted_at__isnull=True).exists()

    def puede_facturarse(self):
        return self.estado_pedido == 'COMPLETADO' and self.estado_facturacion == 'NO_FACTURADO'

    def calcular_total(self):
        """Calcula el total del pedido desde los detalles"""
        detalles = self.detallepedido_set.filter(deleted_at__isnull=True)
        total = sum(d.subtotal for d in detalles)
        self.total_pedido = total
        self.save()
    
    def cambiar_estado(self, nuevo_estado, usuario=None):
        """Cambia el estado del pedido con validaciones"""
        transiciones_validas = {
            'PENDIENTE': ['CONFIRMADO', 'CANCELADO'],
            'CONFIRMADO': ['EN PROCESO', 'CANCELADO'],
            'EN PROCESO': ['COMPLETADO', 'CANCELADO'],
            'COMPLETADO': [],
            'CANCELADO': []
        }
        
        if nuevo_estado not in transiciones_validas.get(self.estado_pedido, []):
            raise ValidationError(
                f"No se puede cambiar de {self.estado_pedido} a {nuevo_estado}"
            )
        
        self.estado_pedido = nuevo_estado
        
        if nuevo_estado == 'COMPLETADO' and not self.fecha_entrega_estimada:
            self.fecha_entrega_estimada = timezone.now().date()
        
        self.save()

    def get_total_formateado(self):
        return f"${int(self.total_pedido):,}".replace(",", ".")

    def __str__(self):
        return f"{self.numero_pedido} - {self.cliente} ({self.estado_pedido})"
    

class DetallePedido(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    pedido = models.ForeignKey(Pedido, models.DO_NOTHING)
    producto = models.ForeignKey('inventario.Producto', models.DO_NOTHING)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'detalle_pedido'

    def __str__(self):
        # Nota: Este modelo usa IDs en lugar de FKs, así que no podemos acceder al nombre del producto directamente
        return f"Detalle #{self.id_detalle} - Producto ID: {self.producto_id}"
    
    def clean(self):
        if self.cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor a 0")
        if self.precio_unitario < 0:
            raise ValidationError("El precio unitario no puede ser negativo")

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        
        # Calcular subtotal
        self.subtotal = self.cantidad * self.precio_unitario
        
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Recalcular total del pedido
        if self.pedido:
            self.pedido.calcular_total()

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save()
        return self

    def __str__(self):
        return f"{self.producto} x{self.cantidad}"
    
# ============================================================================
# VENTAS
# ============================================================================
class Ventas(models.Model):
    ESTADOS_VENTA = [
        ('PENDIENTE', 'Pendiente'),
        ('COMPLETADA', 'Completada'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    TIPOS_VENTA = [
        ('DIRECTA', 'Venta Directa'),
        ('DESDE_PEDIDO', 'Desde Pedido'),
        ('DESDE_COTIZACION', 'Desde Cotización'),
    ]

    id_venta = models.AutoField(primary_key=True)
    usuario = models.ForeignKey('usuarios.Usuarios', models.DO_NOTHING, blank=True, null=True)
    cliente = models.ForeignKey(Clientes, models.DO_NOTHING, blank=True, null=True)
    pedido = models.OneToOneField(Pedido, models.DO_NOTHING, blank=True, null=True)
    tipo_venta = models.CharField(
        max_length=20,
        choices=TIPOS_VENTA,
        default='DIRECTA'
    )
    foto_orden = models.CharField(max_length=255, blank=True, null=True)
    fecha_venta = models.DateTimeField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    observaciones = models.TextField(blank=True, null=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado_venta = models.CharField(max_length=10, choices=ESTADOS_VENTA, default='PENDIENTE')
    metodo_pago = models.ForeignKey(MetodosPago, models.DO_NOTHING, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    numero_factura = models.CharField(max_length=50, blank=True, null=True)
    prefijo = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'ventas'
        ordering = ['-fecha_venta', '-created_at']
        indexes = [
            models.Index(fields=['estado_venta']),
            models.Index(fields=['cliente']),
            models.Index(fields=['fecha_venta']),
        ]

    def precio_formateado(self):
        """
        Retorna el precio formateado sin decimales y con separador de miles
        Ejemplo: 950000 → $950.000
        """
        return f"{int(self.total):,}".replace(",", ".")
    
    def __str__(self):
        cliente_name = self.cliente.nombre if self.cliente else "Sin cliente"
        return f"Venta #{self.id_venta} - {cliente_name}"
    
    def clean(self):
        if self.subtotal < 0:
            raise ValidationError("El subtotal no puede ser negativo")
        if self.impuesto < 0:
            raise ValidationError("El impuesto no puede ser negativo")
        if self.descuento < 0:
            raise ValidationError("El descuento no puede ser negativo")
        if self.total < 0:
            raise ValidationError("El total no puede ser negativo")
        
        # Validar consistencia
        total_calculado = self.subtotal + self.impuesto - self.descuento
        if abs(float(self.total) - float(total_calculado)) > 0.01:
            raise ValidationError(f"El total debe ser subtotal + impuesto - descuento ({total_calculado})")

    def save(self, *args, **kwargs):
        if not self.pk and not self.created_at:
            self.created_at = timezone.now()
            if not self.numero_factura:
                # Generar número de factura
                self.prefijo = self.prefijo or 'FAC'
                ultimo = Ventas.objects.filter(
                    prefijo=self.prefijo,
                    deleted_at__isnull=True
                ).order_by('-id_venta').first()
                consecutivo = (ultimo.id_venta or 0) + 1
                self.numero_factura = f"{self.prefijo}-{consecutivo:06d}"
        
        self.updated_at = timezone.now()
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """Soft delete - solo si está pendiente"""
        if self.estado_venta != 'PENDIENTE':
            raise ValidationError(f"No se puede eliminar una venta en estado {self.estado_venta}")
        self.deleted_at = timezone.now()
        self.save()
        return self

    def puede_modificarse(self):
        return self.estado_venta == 'PENDIENTE'

    def puede_eliminarse(self):
        return self.estado_venta == 'PENDIENTE'

    def calcular_totales(self):
        """Calcula totales desde los detalles"""
        detalles = self.detalleventa_set.filter(deleted_at__isnull=True)
        
        subtotal = sum(d.subtotal for d in detalles)
        impuesto = subtotal * Decimal('0.19')  # 19% IVA
        descuento = self.descuento or 0
        total = subtotal + impuesto - descuento
        
        self.subtotal = subtotal
        self.impuesto = impuesto
        self.total = total
        self.save()

    def completar_venta(self):
        """Marca la venta como completada"""
        if self.estado_venta != 'PENDIENTE':
            raise ValidationError("Solo se pueden completar ventas pendientes")
        
        self.estado_venta = 'COMPLETADA'
        self.save()
        
        # Si tiene pedido asociado, actualizarlo
        if self.pedido:
            self.pedido.estado_pedido = 'COMPLETADO'
            self.pedido.estado_facturacion = 'FACTURADO'
            self.pedido.fecha_facturacion = timezone.now()
            self.pedido.usuario_facturo = self.usuario
            self.pedido.save()

    def get_total_formateado(self):
        return f"${int(self.total):,}".replace(",", ".")

    def __str__(self):
        cliente_name = self.cliente.nombre if self.cliente else "Sin cliente"
        return f"{self.numero_factura} - {cliente_name}"


class DetalleVenta(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    venta = models.ForeignKey(Ventas, models.DO_NOTHING)
    producto = models.ForeignKey('inventario.Producto', models.DO_NOTHING)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    costo_estimado = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'detalle_venta'

    def __str__(self):
        return f"{self.producto} x{self.cantidad}"
    
    def clean(self):
        if self.cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor a 0")
        if self.precio_unitario < 0:
            raise ValidationError("El precio unitario no puede ser negativo")
        if self.descuento < 0:
            raise ValidationError("El descuento no puede ser negativo")

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        
        # Calcular subtotal
        self.subtotal = (self.cantidad * self.precio_unitario) - self.descuento
        
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Recalcular totales de la venta
        if self.venta:
            self.venta.calcular_totales()

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save()
        return self

    def __str__(self):
        return f"{self.producto} x{self.cantidad}"