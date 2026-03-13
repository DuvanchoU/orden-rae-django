from django import forms
from .models import Clientes, Pedido, Ventas, Cotizaciones

class ClienteForm(forms.ModelForm):
    # Campo de estado con opciones predefinidas
    estado = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el estado'),
            ('ACTIVO', 'ACTIVO'),
            ('INACTIVO', 'INACTIVO'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Clientes
        fields = ['nombre', 'apellido', 'telefono', 'email', 'direccion', 'estado']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del cliente'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+57 300 123 4567'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'cliente@email.com'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección completa'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # No necesitamos empty_label para estado porque ya lo definimos en choices

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
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Pedido
        fields = ['cliente', 'fecha_entrega_estimada', 'total_pedido', 
                  'estado_pedido', 'direccion_entrega',]
        widgets = {
            'fecha_entrega_estimada': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'total_pedido': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'direccion_entrega': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección completa de entrega'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar el texto de los selects
        self.fields['cliente'].empty_label = "Seleccione un cliente"
        # No necesitamos empty_label para estado porque ya lo definimos en choices

class VentaForm(forms.ModelForm):
    estado_venta = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el estado'),
            ('PENDIENTE', 'PENDIENTE'),
            ('COMPLETADA', 'COMPLETADA'),
            ('CANCELADA', 'CANCELADA'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
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
        self.fields['cliente'].empty_label = "Seleccione un cliente"
        self.fields['pedido'].empty_label = "Seleccione un pedido (opcional)"
        self.fields['metodo_pago'].empty_label = "Seleccione método de pago"


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
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Cotizaciones
        fields = ['cliente', 'fecha_cotizacion', 'fecha_vencimiento', 
                  'validez_dias', 'tiempo_entrega', 'moneda',
                  'subtotal', 'impuesto', 'descuento', 'total',
                  'estado', 'requiere_produccion', 'observaciones']
        widgets = {
            'fecha_cotizacion': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'validez_dias': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '30'}),
            'subtotal': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'impuesto': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'descuento': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'total': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones adicionales'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].empty_label = "Seleccione un cliente"