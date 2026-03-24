// static/js/carrito.js - FUNCIÓN CORREGIDA
async function actualizarContadorCarrito() {
    try {
        //  URL correcta según tu urls.py
        const url = '/ventas/api/carrito/contador/';
            
        const res = await fetch(url);
        
        // Verificar que la respuesta sea JSON válido
        if (!res.ok) {
            console.error(' Error HTTP:', res.status);
            return 0;
        }
        
        const data = await res.json();
        const cantidad = data.cantidad || 0;
        
        // Actualizar TODOS los elementos con id="contador-carrito"
        document.querySelectorAll('#contador-carrito').forEach(el => {
            el.textContent = cantidad;
            el.style.display = cantidad > 0 ? 'inline-block' : 'none';
            el.dataset.cantidad = cantidad;
        });
        
        console.log(' Contador actualizado:', cantidad);
        return cantidad;
    } catch (e) {
        console.error(' Error al actualizar contador:', e);
        return 0;
    }
}

// Hacer la función accesible globalmente
window.actualizarContadorCarrito = actualizarContadorCarrito;
window.actualizarContadorGlobal = actualizarContadorCarrito;

// Ejecutar al cargar cualquier página
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        actualizarContadorCarrito();
    }, 100);
});

// Escuchar eventos personalizados
document.addEventListener('carritoActualizado', () => {
    actualizarContadorCarrito();
});