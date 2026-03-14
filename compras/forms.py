from django import forms
from .models import Compras

class CompraForm(forms.ModelForm):
    estado = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el estado'),
            ('PENDIENTE', 'PENDIENTE'),
            ('RECIBIDA', 'RECIBIDA'),
            ('CANCELADA', 'CANCELADA'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Compras
        fields = ['proveedor', 'fecha_compra', 'total_compra', 'estado', 'foto_orden']
        widgets = {
            'fecha_compra': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'total_compra': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'foto_orden': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proveedor'].empty_label = "Seleccione un proveedor"