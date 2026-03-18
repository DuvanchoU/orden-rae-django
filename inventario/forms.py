from django import forms
from .models import Inventario, Producto, Categorias, Bodegas, Proveedores
from django.core.exceptions import ValidationError

class ProductoForm(forms.ModelForm):
    # Campo manual para el proveedor (ya que el modelo usa proveedor_id como entero)
    proveedor = forms.ModelChoiceField(
        queryset=Proveedores.objects.filter(estado='ACTIVO', deleted_at__isnull=True).order_by('nombre'),
        required=False,
        empty_label="Seleccione un proveedor (Opcional)",
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label="Proveedor"
    )

    class Meta:
        model = Producto
        fields = ['codigo_producto', 'referencia_producto', 'categoria', 'tipo_madera', 
                  'color_producto', 'precio_actual', 'estado', 'proveedor']
        widgets = {
            'codigo_producto': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ej: CUN-001',
                'required': True
            }),
            'referencia_producto': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Descripción del producto'
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'tipo_madera': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Tipo de madera'
            }),
            'color_producto': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Color'
            }),
            'precio_actual': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': '0',
                'step': '0.01',
                'min': '0.01'
            }),
            'estado': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].empty_label = "Seleccione una categoría"
        # Asegurar que las opciones de estado coincidan con el modelo
        self.fields['estado'].choices = Producto._meta.get_field('estado').choices

        # Si estamos editando y hay un proveedor guardado, seleccionarlo
        if self.instance.pk and self.instance.proveedor_id:
            try:
                self.fields['proveedor'].initial = self.instance.proveedor_id
            except Proveedores.DoesNotExist:
                pass

    def clean_codigo_producto(self):
        codigo = self.cleaned_data.get('codigo_producto')
        queryset = Producto.objects.filter(codigo_producto=codigo)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError("Este código de producto ya existe.")
        return codigo

    def clean_precio_actual(self):
        precio = self.cleaned_data.get('precio_actual')
        if precio is None or precio <= 0:
            raise ValidationError("El precio debe ser mayor a cero.")
        return precio
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Asignar el ID del proveedor seleccionado al campo proveedor_id del modelo
        proveedor = self.cleaned_data.get('proveedor')
        if proveedor:
            instance.proveedor_id = proveedor.id_proveedor
        else:
            instance.proveedor_id = None
            
        if commit:
            instance.save()
        return instance
    
class InventarioForm(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ['producto', 'bodega', 'proveedor', 'cantidad_disponible', 'fecha_llegada', 'estado']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'bodega': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
            'cantidad_disponible': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'required': True}),
            'fecha_llegada': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-select', 'required': True}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].empty_label = "Seleccione un producto"
        self.fields['bodega'].empty_label = "Seleccione una bodega"
        self.fields['proveedor'].empty_label = "Seleccione un proveedor (Opcional)"
        self.fields['proveedor'].required = False
        
        # Opciones de estado dinámicas
        self.fields['estado'].choices = [
            ('', 'Seleccione el estado'),
            ('DISPONIBLE', 'DISPONIBLE'),
            ('RESERVADO', 'RESERVADO'),
            ('AGOTADO', 'AGOTADO'),
        ]

class BodegaForm(forms.ModelForm):
    class Meta:
        model = Bodegas
        fields = ['nombre_bodega', 'direccion', 'estado']
        widgets = {
            'nombre_bodega': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: PRINCIPAL', 'required': True}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección de la bodega'}),
            'estado': forms.Select(attrs={'class': 'form-select', 'required': True}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['estado'].choices = [
            ('', 'Seleccione el estado'),
            ('ACTIVA', 'ACTIVA'),
            ('INACTIVA', 'INACTIVA'),
        ]

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categorias
        fields = ['nombre_categoria', 'estado_categoria']
        widgets = {
            'nombre_categoria': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: CUNAS', 'required': True}),
            'estado_categoria': forms.Select(attrs={'class': 'form-select', 'required': True}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['estado_categoria'].choices = [
            ('', 'Seleccione el estado'),
            ('activo', 'ACTIVO'),
            ('inactivo', 'INACTIVO'),
        ]

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedores
        fields = ['nombre', 'telefono', 'email', 'direccion', 'estado']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del proveedor', 'required': True}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+57 300 123 4567'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'contacto@empresa.com'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección completa'}),
            'estado': forms.Select(attrs={'class': 'form-select', 'required': True}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['estado'].choices = [
            ('', 'Seleccione el estado'),
            ('ACTIVO', 'ACTIVO'),
            ('INACTIVO', 'INACTIVO'),
        ]