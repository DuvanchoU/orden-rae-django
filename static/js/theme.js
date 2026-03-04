document.addEventListener("DOMContentLoaded", () => {
    const body = document.body;
    const toggle = document.getElementById("themeToggle");

  // Tema guardado
    const savedTheme = localStorage.getItem("theme") || "theme-dark";
    body.classList.add(savedTheme);
    toggle.innerHTML = savedTheme === "theme-dark"
    ? '<i class="bi bi-moon-fill me-1"></i> Modo oscuro'
    : '<i class="bi bi-sun-fill me-1"></i> Modo claro';

    toggle.addEventListener("click", () => {
    const isDark = body.classList.contains("theme-dark");

    body.classList.toggle("theme-dark", !isDark);
    body.classList.toggle("theme-light", isDark);

    localStorage.setItem("theme", isDark ? "theme-light" : "theme-dark");

    toggle.innerHTML = isDark
        ? '<i class="bi bi-sun-fill me-1"></i> Modo claro'
        : '<i class="bi bi-moon-fill me-1"></i> Modo oscuro';
    });
});