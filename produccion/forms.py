from django import forms
from .models import Produccion
from inventario.models import Producto, Proveedores
from django.utils import timezone
from datetime import date

class ProduccionForm(forms.ModelForm):
    # Campo de estado con opciones predefinidas
    estado_produccion = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el estado'),
            ('PENDIENTE', 'PENDIENTE'),
            ('EN PROCESO', 'EN PROCESO'),
            ('TERMINADA', 'TERMINADA'),
            ('CANCELADA', 'CANCELADA'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Produccion
        fields = ['producto', 'cantidad_producida', 'fecha_inicio', 'fecha_fin', 
                  'estado_produccion', 'proveedor', 'observaciones']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'cantidad_producida': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': '0',
                'min': '1',
                'max': '1000000'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Observaciones adicionales (opcional)'
            }),
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ordenar productos alfabéticamente por código_producto
        self.fields['producto'].queryset = Producto.objects.filter(
            deleted_at__isnull=True
        ).order_by('codigo_producto')
        
        # Ordenar proveedores alfabéticamente
        self.fields['proveedor'].queryset = Proveedores.objects.filter(
            deleted_at__isnull=True
        ).order_by('nombre')
        # Personalizar el texto de los selects
        self.fields['producto'].empty_label = "Seleccione un producto"
        self.fields['proveedor'].empty_label = "Seleccione un proveedor"

        # Valores por defecto para fechas
        if not self.instance.pk:  # Solo para creación
            self.fields['fecha_inicio'].initial = date.today()
            self.fields['estado_produccion'].initial = 'PENDIENTE'

    def clean_cantidad_producida(self):
        """Validación de cantidad"""
        cantidad = self.cleaned_data.get('cantidad_producida')
        
        if cantidad is None or cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor a 0")
        
        if cantidad > 1000000:
            raise forms.ValidationError("Cantidad máxima excedida (1,000,000)")
        
        # Si es edición, validar contra cantidad asignada
        if self.instance.pk:
            cantidad_asignada = self.instance.get_cantidad_asignada()
            if cantidad < cantidad_asignada:
                raise forms.ValidationError(
                    f"No se puede reducir. Hay {cantidad_asignada} und. asignadas a pedidos"
                )
        
        return cantidad

    def clean_fecha_fin(self):
        """Validación de fecha fin"""
        fecha_fin = self.cleaned_data.get('fecha_fin')
        fecha_inicio = self.cleaned_data.get('fecha_inicio')
        
        if fecha_fin and fecha_inicio:
            if fecha_fin < fecha_inicio:
                raise forms.ValidationError(
                    "La fecha de fin no puede ser anterior a la fecha de inicio"
                )
        
        return fecha_fin

    def clean(self):
        """Validaciones cruzadas"""
        cleaned_data = super().clean()
        
        estado = cleaned_data.get('estado_produccion')
        fecha_fin = cleaned_data.get('fecha_fin')
        fecha_inicio = cleaned_data.get('fecha_inicio')
        
        # Si está TERMINADA, debe tener fecha de fin
        if estado == 'TERMINADA' and not fecha_fin:
            self.add_error(
                'fecha_fin',
                "La producción terminada debe tener fecha de fin"
            )
        
        # Si está TERMINADA, fecha_inicio debe estar definida
        if estado == 'TERMINADA' and not fecha_inicio:
            self.add_error(
                'fecha_inicio',
                "La producción terminada debe tener fecha de inicio"
            )
        
        # Validar que no se pueda crear directamente como TERMINADA sin fechas
        if not self.instance.pk and estado == 'TERMINADA':
            if not fecha_inicio or not fecha_fin:
                self.add_error(
                    'estado_produccion',
                    "Para crear una producción terminada, debe completar ambas fechas"
                )
        
        return cleaned_data