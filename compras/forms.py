from django import forms
from django.utils import timezone
from .models import Compras, DetalleCompra
from inventario.models import Producto, Proveedores
from decimal import Decimal


class CompraForm(forms.ModelForm):
    estado = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el estado'),
            ('PENDIENTE', 'PENDIENTE'),
            ('RECIBIDA', 'RECIBIDA'),
            ('CANCELADA', 'CANCELADA'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    class Meta:
        model = Compras
        fields = ['proveedor', 'fecha_compra', 'total_compra', 'estado', 'foto_orden']
        widgets = {
            'fecha_compra': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'max': timezone.now().date().isoformat()}),
            'total_compra': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'foto_orden': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proveedor'].queryset = Proveedores.objects.filter(
            estado='ACTIVO',
            deleted_at__isnull=True
        ).order_by('nombre')
        self.fields['proveedor'].empty_label = "Seleccione un proveedor"
        
        # Si es edición, permitir todos los estados
        if not self.instance.pk:
            self.fields['estado'].initial = 'PENDIENTE'
            self.fields['estado'].widget.attrs['disabled'] = True

    def clean_proveedor(self):
        proveedor = self.cleaned_data.get('proveedor')
        if proveedor and proveedor.estado != 'ACTIVO':
            raise forms.ValidationError("El proveedor seleccionado está inactivo")
        return proveedor

    def clean_fecha_compra(self):
        fecha = self.cleaned_data.get('fecha_compra')
        if fecha and fecha > timezone.now().date():
            raise forms.ValidationError("La fecha de compra no puede ser futura")
        return fecha


class DetalleCompraForm(forms.ModelForm):
    class Meta:
        model = DetalleCompra
        fields = ['compra', 'producto', 'cantidad', 'precio_unitario']
        widgets = {
            'compra': forms.Select(attrs={'class': 'form-select'}),
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
        
        # Filtrar solo compras pendientes
        self.fields['compra'].queryset = Compras.objects.filter(
            estado='PENDIENTE',
            deleted_at__isnull=True
        ).order_by('-fecha_compra')
        self.fields['compra'].empty_label = "Seleccione una compra"
        
        # Filtrar productos disponibles
        self.fields['producto'].queryset = Producto.objects.filter(
            deleted_at__isnull=True
        ).order_by('codigo_producto')
        self.fields['producto'].empty_label = "Seleccione un producto"
        
        # Si es edición, cargar precio del producto
        if self.instance.pk and self.instance.producto:
            self.fields['precio_unitario'].initial = self.instance.producto.precio_actual

    def clean_compra(self):
        compra = self.cleaned_data.get('compra')
        if compra and compra.estado != 'PENDIENTE':
            raise forms.ValidationError("Solo se pueden agregar productos a compras PENDIENTE")
        return compra

    def clean_producto(self):
        producto = self.cleaned_data.get('producto')
        if producto and producto.estado != 'DISPONIBLE':
            raise forms.ValidationError(f"El producto {producto.codigo_producto} no está disponible")
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
        compra = cleaned_data.get('compra')
        producto = cleaned_data.get('producto')
        cantidad = cleaned_data.get('cantidad')
        
        # Validar que no se duplique el producto en la misma compra
        if compra and producto:
            existe = DetalleCompra.objects.filter(
                compra=compra,
                producto=producto,
                deleted_at__isnull=True
            )
            if self.instance.pk:
                existe = existe.exclude(pk=self.instance.pk)
            
            if existe.exists():
                raise forms.ValidationError(
                    "Este producto ya está en la compra. Edite la cantidad existente."
                )
        
        return cleaned_data