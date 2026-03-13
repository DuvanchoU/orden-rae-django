from django import forms
from .models import Clientes, Pedido

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