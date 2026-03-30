from django import forms
from .models import Usuarios, RolesOld
from django.contrib.auth.hashers import make_password
import re

class UsuarioForm(forms.ModelForm):
    # Confirmación de contraseña
    confirmar_contrasena = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmar contraseña'
        }),
        label="Confirmar Contraseña"
    )
    
    estado = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el estado'),
            ('ACTIVO', 'ACTIVO'),
            ('INACTIVO', 'INACTIVO'),
            ('SUSPENDIDO', 'SUSPENDIDO'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    genero = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el género'),
            ('M', 'Masculino'),
            ('F', 'Femenino'),
            ('O', 'Otro'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    class Meta:
        model = Usuarios
        fields = ['nombres', 'apellidos', 'documento', 'correo_usuario', 
                  'contrasena_usuario', 'telefono', 'genero', 'id_rol', 'estado']
        widgets = {
            'nombres': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nombres del usuario',
                'autocomplete': 'given-name'
            }),
            'apellidos': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Apellidos del usuario',
                'autocomplete': 'family-name'
            }),
            'documento': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Número de documento',
                'autocomplete': 'off'
            }),
            'correo_usuario': forms.EmailInput(attrs={
                'class': 'form-control', 
                'placeholder': 'correo@ejemplo.com',
                'autocomplete': 'email'
            }),
            'contrasena_usuario': forms.PasswordInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Mínimo 8 caracteres, 1 mayúscula, 1 número',
                'autocomplete': 'new-password'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '+57 300 123 4567',
                'autocomplete': 'tel'
            }),
            'id_rol': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['id_rol'].queryset = RolesOld.objects.filter(
            deleted_at__isnull=True
        ).order_by('nombre_rol')
        self.fields['id_rol'].empty_label = "Seleccione un rol"
        self.fields['estado'].initial = 'ACTIVO'

    def clean_documento(self):
        documento = self.cleaned_data.get('documento', '').strip()
        
        if not documento:
            raise forms.ValidationError("El documento es obligatorio")
        
        if len(documento) < 5:
            raise forms.ValidationError("El documento debe tener al menos 5 caracteres")
        
        documento_limpio = documento.replace('-', '').replace('.', '')
        if not documento_limpio.isdigit():
            raise forms.ValidationError("El documento solo debe contener números")
        
        # Verificar unicidad
        queryset = Usuarios.objects.filter(documento=documento, deleted_at__isnull=True)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise forms.ValidationError("El documento ya está registrado")
        
        return documento

    def clean_correo_usuario(self):
        correo = self.cleaned_data.get('correo_usuario', '').lower().strip()
        
        if not correo:
            raise forms.ValidationError("El correo electrónico es obligatorio")
        
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, correo):
            raise forms.ValidationError("El correo electrónico no es válido")
        
        # Verificar unicidad
        queryset = Usuarios.objects.filter(correo_usuario=correo, deleted_at__isnull=True)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise forms.ValidationError("El correo electrónico ya está registrado")
        
        return correo

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        
        if telefono:
            telefono = telefono.strip()
            telefono_limpio = re.sub(r'[^\d+]', '', telefono)
            
            if len(telefono_limpio) < 7:
                raise forms.ValidationError("El teléfono debe tener al menos 7 dígitos")
            
            if len(telefono_limpio) > 15:
                raise forms.ValidationError("El teléfono no puede tener más de 15 dígitos")
            
            return telefono_limpio
        
        return telefono

    def clean_contrasena_usuario(self):
        contrasena = self.cleaned_data.get('contrasena_usuario')
        
        if not contrasena:
            raise forms.ValidationError("La contraseña es obligatoria")
        
        if len(contrasena) < 8:
            raise forms.ValidationError("La contraseña debe tener al menos 8 caracteres")
        
        if not re.search(r'[A-Z]', contrasena):
            raise forms.ValidationError("La contraseña debe contener al menos una letra mayúscula")
        
        if not re.search(r'[a-z]', contrasena):
            raise forms.ValidationError("La contraseña debe contener al menos una letra minúscula")
        
        if not re.search(r'\d', contrasena):
            raise forms.ValidationError("La contraseña debe contener al menos un número")
        
        return contrasena

    def clean_confirmar_contrasena(self):
        confirmar = self.cleaned_data.get('confirmar_contrasena')
        contrasena = self.cleaned_data.get('contrasena_usuario')
        
        if confirmar and contrasena and confirmar != contrasena:
            raise forms.ValidationError("Las contraseñas no coinciden")
        
        return confirmar

    def clean(self):
        cleaned_data = super().clean()
        nombres = cleaned_data.get('nombres')
        apellidos = cleaned_data.get('apellidos')
        
        if nombres and len(nombres.strip()) < 2:
            self.add_error('nombres', "Los nombres deben tener al menos 2 caracteres")
        
        if apellidos and len(apellidos.strip()) < 2:
            self.add_error('apellidos', "Los apellidos deben tener al menos 2 caracteres")
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Hashear contraseña
        if self.cleaned_data.get('contrasena_usuario'):
            instance.contrasena_usuario = make_password(self.cleaned_data['contrasena_usuario'])
        
        if commit:
            instance.save()
        
        return instance


class UsuarioUpdateForm(forms.ModelForm):
    estado = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el estado'),
            ('ACTIVO', 'ACTIVO'),
            ('INACTIVO', 'INACTIVO'),
            ('SUSPENDIDO', 'SUSPENDIDO'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    genero = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el género'),
            ('M', 'Masculino'),
            ('F', 'Femenino'),
            ('O', 'Otro'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    class Meta:
        model = Usuarios
        fields = ['nombres', 'apellidos', 'documento', 'correo_usuario', 
                  'telefono', 'genero', 'id_rol', 'estado']
        widgets = {
            'nombres': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nombres del usuario'
            }),
            'apellidos': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Apellidos del usuario'
            }),
            'documento': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Número de documento'
            }),
            'correo_usuario': forms.EmailInput(attrs={
                'class': 'form-control', 
                'placeholder': 'correo@ejemplo.com'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '+57 300 123 4567'
            }),
            'id_rol': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['id_rol'].queryset = RolesOld.objects.filter(
            deleted_at__isnull=True
        ).order_by('nombre_rol')
        self.fields['id_rol'].empty_label = "Seleccione un rol"

    def clean_documento(self):
        documento = self.cleaned_data.get('documento', '').strip()
        
        if documento:
            if len(documento) < 5:
                raise forms.ValidationError("El documento debe tener al menos 5 caracteres")
            
            documento_limpio = documento.replace('-', '').replace('.', '')
            if not documento_limpio.isdigit():
                raise forms.ValidationError("El documento solo debe contener números")
            
            queryset = Usuarios.objects.filter(documento=documento, deleted_at__isnull=True)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError("El documento ya está registrado")
        
        return documento

    def clean_correo_usuario(self):
        correo = self.cleaned_data.get('correo_usuario', '').lower().strip()
        
        if correo:
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, correo):
                raise forms.ValidationError("El correo electrónico no es válido")
            
            queryset = Usuarios.objects.filter(correo_usuario=correo, deleted_at__isnull=True)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError("El correo electrónico ya está registrado")
        
        return correo


class RolForm(forms.ModelForm):
    class Meta:
        model = RolesOld
        fields = ['nombre_rol', 'descripcion']
        widgets = {
            'nombre_rol': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ej: Administrador',
                'maxlength': '50'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4, 
                'placeholder': 'Describe las funciones y permisos de este rol',
                'maxlength': '500'
            }),
        }
    
    def clean_nombre_rol(self):
        nombre = self.cleaned_data.get('nombre_rol', '').strip().upper()
        
        if not nombre:
            raise forms.ValidationError("El nombre del rol es obligatorio")
        
        if len(nombre) < 3:
            raise forms.ValidationError("El nombre del rol debe tener al menos 3 caracteres")
        
        # Verificar unicidad
        queryset = RolesOld.objects.filter(nombre_rol=nombre, deleted_at__isnull=True)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise forms.ValidationError("Ya existe un rol con ese nombre")
        
        return nombre

    def clean_descripcion(self):
        descripcion = self.cleaned_data.get('descripcion')
        
        if descripcion and len(descripcion.strip()) < 10:
            raise forms.ValidationError("La descripción debe tener al menos 10 caracteres")
        
        return descripcion