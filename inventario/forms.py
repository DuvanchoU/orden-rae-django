from django import forms
from .models import Inventario, Producto, Categorias, Bodegas, Proveedores

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['codigo_producto', 'referencia_producto', 'categoria', 'tipo_madera', 
                  'color_producto', 'precio_actual', 'estado']
        widgets = {
            'codigo_producto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: CUN-001'}),
            'referencia_producto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descripción del producto'}),
            'tipo_madera': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tipo de madera'}),
            'color_producto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Color'}),
            'precio_actual': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar el texto de los selects
        self.fields['categoria'].empty_label = "Seleccione una categoría"
    
class InventarioForm(forms.ModelForm):
    # Campo de estado con opciones predefinidas
    estado = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el estado'),
            ('DISPONIBLE', 'DISPONIBLE'),
            ('RESERVADO', 'RESERVADO'),
            ('AGOTADO', 'AGOTADO'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Inventario
        fields = ['producto', 'bodega', 'proveedor', 'cantidad_disponible', 'fecha_llegada', 'estado']
        widgets = {
            'fecha_llegada': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar el texto de los selects
        self.fields['producto'].empty_label = "Seleccione un producto"
        self.fields['bodega'].empty_label = "Seleccione una bodega"
        self.fields['proveedor'].empty_label = "Seleccione un proveedor"

class BodegaForm(forms.ModelForm):
    # Campo de estado con opciones predefinidas
    estado = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el estado'),
            ('ACTIVA', 'ACTIVA'),
            ('INACTIVA', 'INACTIVA'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Bodegas
        fields = ['nombre_bodega', 'direccion', 'estado']
        widgets = {
            'nombre_bodega': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: PRINCIPAL'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección de la bodega'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # No necesitamos empty_label para estado porque ya lo definimos en choices

class CategoriaForm(forms.ModelForm):
    # Campo de estado con opciones predefinidas
    estado_categoria = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el estado'),
            ('activo', 'ACTIVO'),
            ('inactivo', 'INACTIVO'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Categorias
        fields = ['nombre_categoria', 'estado_categoria']
        widgets = {
            'nombre_categoria': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ej: CUNAS'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class ProveedorForm(forms.ModelForm):
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
        model = Proveedores
        fields = ['nombre', 'telefono', 'email', 'direccion', 'estado']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del proveedor'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+57 300 123 4567'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'contacto@empresa.com'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección completa'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # No necesitamos empty_label para estado porque ya lo definimos en choices