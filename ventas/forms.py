from django import forms
from .models import Clientes, Pedido, Ventas, Cotizaciones, DetallePedido, DetalleVenta, DetalleCotizacion
from inventario.models import Producto
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum

import re

class ClienteForm(forms.ModelForm):
    # Campo de estado con opciones predefinidas
    estado = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el estado'),
            ('ACTIVO', 'ACTIVO'),
            ('INACTIVO', 'INACTIVO'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    class Meta:
        model = Clientes
        fields = ['nombre', 'apellido', 'telefono', 'email', 'direccion', 'estado']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nombre del cliente',
                'required': True,
                'autocomplete': 'given-name'
            }),
            'apellido': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Apellido (opcional)',
                'autocomplete': 'family-name'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '+57 300 123 4567',
                'pattern': r'^[\d+\-\s()]{7,15}$',
                'autocomplete': 'tel'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control', 
                'placeholder': 'cliente@email.com',
                'autocomplete': 'email'
            }),
            'direccion': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Dirección completa',
                'autocomplete': 'street-address'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['estado'].initial = 'ACTIVO'
    
    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()
        
        if not nombre:
            raise forms.ValidationError("El nombre es obligatorio")
        
        if len(nombre) < 2:
            raise forms.ValidationError("El nombre debe tener al menos 2 caracteres")
        
        if len(nombre) > 100:
            raise forms.ValidationError("El nombre no puede exceder 100 caracteres")
        
        # Validar que no sean solo números
        if nombre.isdigit():
            raise forms.ValidationError("El nombre no puede ser solo números")
        
        return nombre.title()

    def clean_apellido(self):
        apellido = self.cleaned_data.get('apellido')
        
        if apellido:
            apellido = apellido.strip()
            if len(apellido) < 2:
                raise forms.ValidationError("El apellido debe tener al menos 2 caracteres")
            return apellido.title()
        
        return apellido

    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        if email:
            email = email.lower().strip()
            
            # Validación de formato de email
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, email):
                raise forms.ValidationError("El email no es válido")
            
            # Verificar si ya existe (excluyendo el actual si es edición)
            queryset = Clientes.objects.filter(email=email, deleted_at__isnull=True)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError(f"El email '{email}' ya está registrado")
        
        return email

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        
        if telefono:
            telefono = telefono.strip()
            
            # Limpiar teléfono (solo dígitos y +)
            telefono_limpio = re.sub(r'[^\d+]', '', telefono)
            
            if len(telefono_limpio) < 7:
                raise forms.ValidationError("El teléfono debe tener al menos 7 dígitos")
            
            if len(telefono_limpio) > 15:
                raise forms.ValidationError("El teléfono no puede tener más de 15 dígitos")
            
            return telefono_limpio
        
        return telefono

    def clean_direccion(self):
        direccion = self.cleaned_data.get('direccion')
        
        if direccion:
            direccion = direccion.strip()
            if len(direccion) < 5:
                raise forms.ValidationError("La dirección debe tener al menos 5 caracteres")
            if len(direccion) > 255:
                raise forms.ValidationError("La dirección no puede exceder 255 caracteres")
        
        return direccion

    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get('nombre')
        apellido = cleaned_data.get('apellido')
        
        # Validar que al menos tenga nombre
        if not nombre and not apellido:
            raise forms.ValidationError("Debe ingresar al menos el nombre del cliente")
        
        return cleaned_data
    
# ============================================================================
# PEDIDOS
# ============================================================================
class PedidoForm(forms.ModelForm):
    # Campo de estado con opciones predefinidas
    estado_pedido = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el estado'),
            ('PENDIENTE', 'PENDIENTE'),
            ('CONFIRMADO', 'CONFIRMADO'),
            ('EN PROCESO', 'EN PROCESO'),
            ('COMPLETADO', 'COMPLETADO'),
            ('CANCELADO', 'CANCELADO'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    class Meta:
        model = Pedido
        fields = ['cliente', 'fecha_entrega_estimada', 'total_pedido', 
                  'estado_pedido', 'direccion_entrega',]
        widgets = {
            'fecha_entrega_estimada': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'min': timezone.now().date().isoformat()}),
            'total_pedido': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'direccion_entrega': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección completa de entrega', 'maxlength': '255'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo clientes activos
        self.fields['cliente'].queryset = Clientes.objects.filter(
            estado='ACTIVO',
            deleted_at__isnull=True
        ).order_by('apellido', 'nombre')
        self.fields['cliente'].empty_label = "Seleccione un cliente"
        
        # Si es edición, permitir todos los estados, si es creación, solo pendientes
        if not self.instance.pk:
            self.fields['estado_pedido'].initial = 'PENDIENTE'
            self.fields['estado_pedido'].widget.attrs['disabled'] = True

    def clean_cliente(self):
        cliente = self.cleaned_data.get('cliente')
        if cliente and cliente.estado != 'ACTIVO':
            raise forms.ValidationError("El cliente seleccionado está inactivo")
        return cliente

    def clean_fecha_entrega_estimada(self):
        fecha = self.cleaned_data.get('fecha_entrega_estimada')
        if fecha and fecha < timezone.now().date():
            raise forms.ValidationError("La fecha de entrega no puede ser anterior a hoy")
        return fecha

    def clean_estado_pedido(self):
        estado = self.cleaned_data.get('estado_pedido')
        # Validar transiciones de estado si es edición
        if self.instance.pk and self.instance.estado_pedido:
            transiciones = {
                'PENDIENTE': ['CONFIRMADO', 'CANCELADO'],
                'CONFIRMADO': ['EN PROCESO', 'CANCELADO'],
                'EN PROCESO': ['COMPLETADO', 'CANCELADO'],
                'COMPLETADO': [],
                'CANCELADO': []
            }
            if estado and estado not in transiciones.get(self.instance.estado_pedido, []):
                if estado != self.instance.estado_pedido:  # Permitir mantener el mismo estado
                    raise forms.ValidationError(
                        f"No se puede cambiar de {self.instance.estado_pedido} a {estado}"
                    )
        return estado

    def clean(self):
        cleaned_data = super().clean()
        fecha_entrega = cleaned_data.get('fecha_entrega_estimada')
        estado = cleaned_data.get('estado_pedido')
        
        # Si está completado, debe tener fecha de entrega
        if estado == 'COMPLETADO' and not fecha_entrega:
            self.add_error('fecha_entrega_estimada', "Un pedido completado debe tener fecha de entrega")
        
        return cleaned_data
    
class DetallePedidoForm(forms.ModelForm):
    class Meta:
        model = DetallePedido
        fields = ['producto', 'cantidad', 'precio_unitario']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '10000',
                'value': '1',
                'placeholder': '1'
            }),
            'precio_unitario': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].queryset = Producto.objects.filter(
            deleted_at__isnull=True,
            estado='DISPONIBLE'
        ).order_by('codigo_producto')
        self.fields['producto'].empty_label = "Seleccione un producto"
        
        # Si es edición, cargar precio del producto
        if self.instance.pk and self.instance.producto:
            self.fields['precio_unitario'].initial = self.instance.producto.precio_actual

    def clean_producto(self):
        producto = self.cleaned_data.get('producto')
        if producto and producto.estado != 'DISPONIBLE':
            raise forms.ValidationError("El producto no está disponible")
        return producto

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        if cantidad is None or cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor a 0")
        if cantidad > 10000:
            raise forms.ValidationError("Cantidad máxima excedida (10,000)")
        return cantidad

    def clean_precio_unitario(self):
        precio = self.cleaned_data.get('precio_unitario')
        if precio is not None and precio < 0:
            raise forms.ValidationError("El precio no puede ser negativo")
        return precio

    def clean(self):
        cleaned_data = super().clean()
        producto = cleaned_data.get('producto')
        cantidad = cleaned_data.get('cantidad')
        
        # Validar stock disponible (opcional, si tienes inventario)
        if producto and cantidad:
            try:
                from inventario.models import Inventario
                stock = Inventario.objects.filter(
                    producto=producto,
                    deleted_at__isnull=True
                ).aggregate(total=Sum('cantidad_disponible'))['total'] or 0
                
                if cantidad > stock:
                    self.add_error('cantidad', f"Stock insuficiente. Disponible: {stock}")
            except:
                pass  # Si no hay módulo de inventario, omitir validación
        
        return cleaned_data
    
# ============================================================================
# VENTAS 
# ============================================================================
class VentaForm(forms.ModelForm):
    estado_venta = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el estado'),
            ('PENDIENTE', 'PENDIENTE'),
            ('COMPLETADA', 'COMPLETADA'),
            ('CANCELADA', 'CANCELADA'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    class Meta:
        model = Ventas
        fields = ['cliente', 'pedido', 'tipo_venta', 'metodo_pago', 
                  'subtotal', 'impuesto', 'descuento', 'total', 
                  'estado_venta', 'observaciones']
        widgets = {
            'subtotal': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'impuesto': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'descuento': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'total': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones adicionales'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].queryset = Clientes.objects.filter(
            estado='ACTIVO',
            deleted_at__isnull=True
        ).order_by('apellido', 'nombre')
        self.fields['cliente'].empty_label = "Seleccione un cliente"
        
        self.fields['pedido'].queryset = Pedido.objects.filter(
            estado_pedido='COMPLETADO',
            deleted_at__isnull=True
        ).order_by('-fecha_pedido')
        self.fields['pedido'].empty_label = "Seleccione un pedido (opcional)"
        
        # Tipo de venta por defecto
        if not self.instance.pk:
            self.fields['tipo_venta'].initial = 'DIRECTA'

    def clean_cliente(self):
        cliente = self.cleaned_data.get('cliente')
        if cliente and cliente.estado != 'ACTIVO':
            raise forms.ValidationError("El cliente seleccionado está inactivo")
        return cliente

    def clean_pedido(self):
        pedido = self.cleaned_data.get('pedido')
        if pedido:
            # Verificar que el pedido no tenga venta asociada
            if Ventas.objects.filter(pedido=pedido, deleted_at__isnull=True).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("Este pedido ya tiene una venta asociada")
            if pedido.estado_pedido != 'COMPLETADO':
                raise forms.ValidationError("Solo se pueden crear ventas desde pedidos COMPLETADOS")
        return pedido

    def clean(self):
        cleaned_data = super().clean()
        cliente = cleaned_data.get('cliente')
        pedido = cleaned_data.get('pedido')
        
        # Debe tener cliente o pedido
        if not cliente and not pedido:
            raise forms.ValidationError("Debe seleccionar un cliente o un pedido")
        
        return cleaned_data

class DetalleVentaForm(forms.ModelForm):
    class Meta:
        model = DetalleVenta
        fields = ['producto', 'cantidad', 'precio_unitario', 'descuento']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '10000',
                'value': '1'
            }),
            'precio_unitario': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'descuento': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'value': '0',
                'placeholder': '0.00'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].queryset = Producto.objects.filter(
            deleted_at__isnull=True
        ).order_by('codigo_producto')
        self.fields['producto'].empty_label = "Seleccione un producto"
        
        if self.instance.pk and self.instance.producto:
            self.fields['precio_unitario'].initial = self.instance.producto.precio_actual

    def clean_producto(self):
        producto = self.cleaned_data.get('producto')
        if producto and producto.deleted_at:
            raise forms.ValidationError("El producto no está disponible")
        return producto

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        if cantidad is None or cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor a 0")
        if cantidad > 10000:
            raise forms.ValidationError("Cantidad máxima excedida (10,000)")
        return cantidad

    def clean_descuento(self):
        descuento = self.cleaned_data.get('descuento') or Decimal('0')
        if descuento < 0:
            raise forms.ValidationError("El descuento no puede ser negativo")
        
        # Validar que descuento no exceda subtotal
        precio = self.cleaned_data.get('precio_unitario')
        cantidad = self.cleaned_data.get('cantidad')
        if precio and cantidad:
            subtotal = precio * cantidad
            if descuento > subtotal:
                raise forms.ValidationError("El descuento no puede exceder el subtotal")
        
        return descuento
    
# ============================================================================
# COTIZACIONES
# ============================================================================
class CotizacionForm(forms.ModelForm):
    estado = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el estado'),
            ('borrador', 'BORRADOR'),
            ('enviada', 'ENVIADA'),
            ('aceptada', 'ACEPTADA'),
            ('rechazada', 'RECHAZADA'),
            ('vencida', 'VENCIDA'),
            ('cancelada', 'CANCELADA'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    class Meta:
        model = Cotizaciones
        fields = ['cliente', 'fecha_cotizacion', 'fecha_vencimiento', 
                  'validez_dias', 'tiempo_entrega', 'moneda',
                  'subtotal', 'impuesto', 'descuento', 'total',
                  'estado', 'requiere_produccion', 'observaciones']
        widgets = {
            'fecha_cotizacion': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'min': timezone.now().date().isoformat()}),
            'validez_dias': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '30', 'min': '1', 'max': '365', 'value': '30'}),
            'subtotal': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'moneda': forms.Select(attrs={'class': 'form-select'}),
            'impuesto': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'descuento': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'total': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones adicionales'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].queryset = Clientes.objects.filter(
            estado='ACTIVO',
            deleted_at__isnull=True
        ).order_by('apellido', 'nombre')
        self.fields['cliente'].empty_label = "Seleccione un cliente"
        
        # Valores por defecto para nueva cotización
        if not self.instance.pk:
            self.fields['validez_dias'].initial = 30
            self.fields['moneda'].initial = 'COP'
            self.fields['estado'].initial = 'borrador'
            self.fields['fecha_vencimiento'].initial = (
                timezone.now().date() + timedelta(days=30)
            ).isoformat()

    def clean_cliente(self):
        cliente = self.cleaned_data.get('cliente')
        if cliente and cliente.estado != 'ACTIVO':
            raise forms.ValidationError("El cliente seleccionado está inactivo")
        return cliente

    def clean_fecha_vencimiento(self):
        fecha = self.cleaned_data.get('fecha_vencimiento')
        fecha_cotizacion = self.cleaned_data.get('fecha_cotizacion') or timezone.now().date()
        
        if fecha and fecha < fecha_cotizacion:
            raise forms.ValidationError("La fecha de vencimiento no puede ser anterior a hoy")
        
        return fecha

    def clean_validez_dias(self):
        dias = self.cleaned_data.get('validez_dias')
        if dias and (dias < 1 or dias > 365):
            raise forms.ValidationError("La validez debe estar entre 1 y 365 días")
        return dias

    def clean_estado(self):
        estado = self.cleaned_data.get('estado')
        
        # Validar transiciones de estado
        if self.instance.pk and self.instance.estado:
            transiciones = {
                'borrador': ['enviada', 'cancelada'],
                'enviada': ['aceptada', 'rechazada', 'vencida', 'cancelada'],
                'aceptada': [],
                'rechazada': [],
                'vencida': [],
                'cancelada': []
            }
            if estado and estado not in transiciones.get(self.instance.estado, []):
                if estado != self.instance.estado:
                    raise forms.ValidationError(
                        f"No se puede cambiar de {self.instance.estado} a {estado}"
                    )
        
        return estado

    def clean(self):
        cleaned_data = super().clean()
        estado = cleaned_data.get('estado')
        fecha_vencimiento = cleaned_data.get('fecha_vencimiento')
        
        # Si está aceptada, debe tener fecha de vencimiento definida
        if estado == 'aceptada' and not fecha_vencimiento:
            self.add_error('fecha_vencimiento', "Una cotización aceptada debe tener fecha de vencimiento")
        
        return cleaned_data
    
class DetalleCotizacionForm(forms.ModelForm):
    class Meta:
        model = DetalleCotizacion
        fields = ['producto', 'cantidad', 'precio_unitario', 'descuento', 'observacion']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '10000',
                'value': '1'
            }),
            'precio_unitario': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'descuento': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'value': '0'
            }),
            'observacion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Observaciones del ítem',
                'maxlength': '255'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].queryset = Producto.objects.filter(
            deleted_at__isnull=True
        ).order_by('codigo_producto')
        self.fields['producto'].empty_label = "Seleccione un producto"
        
        if self.instance.pk and self.instance.producto:
            self.fields['precio_unitario'].initial = self.instance.producto.precio_actual

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        if cantidad is None or cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor a 0")
        if cantidad > 10000:
            raise forms.ValidationError("Cantidad máxima excedida (10,000)")
        return cantidad

    def clean_descuento(self):
        descuento = self.cleaned_data.get('descuento') or Decimal('0')
        if descuento < 0:
            raise forms.ValidationError("El descuento no puede ser negativo")
        return descuento