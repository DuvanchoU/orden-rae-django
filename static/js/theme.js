document.addEventListener("DOMContentLoaded", () => {
    const body = document.body;
    const toggle = document.getElementById("themeToggle");

    // Tema guardado (cambiado a theme-light como default)
    const savedTheme = localStorage.getItem("theme") || "theme-light";
    body.classList.add(savedTheme);
    
    // Actualizar botón al cargar
    updateToggleButton(savedTheme);

    toggle.addEventListener("click", () => {
        const isDark = body.classList.contains("theme-dark");
        
        // Alternar clases
        body.classList.remove(isDark ? "theme-dark" : "theme-light");
        body.classList.add(isDark ? "theme-light" : "theme-dark");
        
        // Guardar nuevo tema
        const newTheme = isDark ? "theme-light" : "theme-dark";
        localStorage.setItem("theme", newTheme);
        
        // Actualizar botón
        updateToggleButton(newTheme);
    });

    // Función para actualizar el botón
    function updateToggleButton(theme) {
        if (theme === "theme-dark") {
            toggle.innerHTML = '<i class="bi bi-sun-fill me-1"></i>Modo claro';
        } else {
            toggle.innerHTML = '<i class="bi bi-moon-fill me-1"></i>Modo oscuro';
        }
    }
});