# 📦 Orden RAE Django - Sistema de Gestión Empresarial

[![Django](https://img.shields.io/badge/Django-4.2-092E20?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python)](https://www.python.org/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap)](https://getbootstrap.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql)](https://www.mysql.com/)

Sistema integral de gestión empresarial desarrollado con **Django** para el control de inventario, ventas, compras, producción y administración de usuarios.

---

# 🧠 Arquitectura del Sistema

El proyecto sigue la arquitectura **MTV (Model Template View)** utilizada por Django.

---

## ✨ **Características**

- 🎨 **Diseño Moderno** - Interfaz minimalista con paleta Slate-Teal
- 📱 **Responsive** - Compatible con dispositivos móviles y desktop
- 🔐 **Seguridad** - Autenticación de usuarios y roles
- 📊 **Reportes** - Vistas detalladas con estadísticas
- 🔍 **Filtros Avanzados** - Búsqueda multicriterio en todos los módulos
- 📄 **Paginación** - Navegación eficiente de grandes volúmenes de datos
- 🎯 **CRUD Completo** - Crear, Leer, Actualizar y Eliminar en todos los módulos

---

## 🗂️ **Módulos del Sistema**

### **📦 Inventario**
| Módulo | Descripción | Estado |
|--------|-------------|--------|
| **Productos** | Catálogo de productos con código, referencia, categoría, precio | ✅ |
| **Bodegas** | Gestión de ubicaciones de almacenamiento | ✅ |
| **Categorías** | Clasificación de productos | ✅ |
| **Proveedores** | Base de datos de proveedores | ✅ |
| **Stock** | Control de existencias por bodega | ✅ |

### **🏭 Producción**
| Módulo | Descripción | Estado |
|--------|-------------|--------|
| **Producción** | Registro y seguimiento de órdenes de producción | ✅ |
| **Estados** | PENDIENTE, EN PROCESO, TERMINADA | ✅ |

### **💰 Ventas**
| Módulo | Descripción | Estado |
|--------|-------------|--------|
| **Clientes** | Base de datos de clientes | ✅ |
| **Pedidos** | Gestión de pedidos de clientes | ✅ |
| **Ventas** | Registro de ventas completadas | ✅ |
| **Cotizaciones** | Generación y seguimiento de cotizaciones | ✅ |

### **🛒 Compras**
| Módulo | Descripción | Estado |
|--------|-------------|--------|
| **Compras** | Órdenes de compra a proveedores | ✅ |
| **Detalle Compra** | Productos por compra | ✅ |

### **👥 Usuarios**
| Módulo | Descripción | Estado |
|--------|-------------|--------|
| **Usuarios** | Gestión de usuarios del sistema | ✅ |
| **Roles** | Roles y permisos de acceso | ✅ |

---

## 🛠️ **Tecnologías**

| Tecnología | Versión | Descripción |
|------------|---------|-------------|
| **Python** | 3.14+ | Lenguaje de programación |
| **Django** | 4.2 | Framework web |
| **Bootstrap** | 5.3 | Framework CSS |
| **MySQL** | 8.0+ | Base de datos |
| **Bootstrap Icons** | 1.11+ | Iconografía |

---

## 📋 **Requisitos**

- Python 3.14 o superior
- MySQL 8.0 o superior
- pip (gestor de paquetes de Python)
- Git (control de versiones)

---

# ⚙️ Instalación

## 1 Clonar repositorio
git clone https://github.com/DuvanchoU/orden-rae-django.git
cd orden-rae-django

---

## 2 Crear entorno virtual
- python -m venv venv
  
---

## 3 Activar entorno virtual
- venv\Scripts\activate

---

## 4 Instalar dependencias
- pip install -r requirements.txt

---

## 5 Configurar base de datos

Editar:

# config/settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'bd_orden_rae_django',
        'USER': 'tu_usuario',
        'PASSWORD': 'tu_contraseña',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}

---

# 6. Ejecutar migraciones
python manage.py migrate

---

# 7. Crear superusuario
python manage.py createsuperuser

---

# 8. Iniciar servidor
python manage.py runserver
