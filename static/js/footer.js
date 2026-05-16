/* ================================================================
   ORDER RAE — footer.js  v2.0
   Funciones: horario en vivo, acordeón mobile, newsletter,
              copiar email, animación de entrada.
================================================================ */

(function () {
    "use strict";

    /* ════════════════════════════════════
       1. AÑO ACTUAL
    ════════════════════════════════════ */
    const yearEl = document.getElementById("ft-year");
    if (yearEl) yearEl.textContent = new Date().getFullYear();

    /* ════════════════════════════════════
       2. INDICADOR HORARIO EN VIVO
    ════════════════════════════════════ */
    (function ftCheckHorario() {
        const now  = new Date();
        const hora = now.getHours();
        const dia  = now.getDay(); // 0=Dom … 6=Sáb
        const dot  = document.getElementById("ft-status-dot");
        const txt  = document.getElementById("ft-status-text");
        if (!dot || !txt) return;

        const esLunSab = dia >= 1 && dia <= 6;
        const esDom    = dia === 0;

        let abierto = false;
        if (esLunSab && hora >= 9  && hora < 18) abierto = true;
        if (esDom    && hora >= 10 && hora < 14) abierto = true;

        if (abierto) {
            dot.classList.add("open");
            txt.textContent = "Abierto ahora · Te respondemos al instante";
        } else {
            dot.classList.add("closed");
            txt.textContent = esDom
                ? "Abrimos Dom 10AM – 2PM"
                : "Abrimos Lun–Sáb 9AM – 6PM";
        }
    })();

    /* ════════════════════════════════════
       3. ACORDEÓN MOBILE
       Llamado desde onclick en el HTML
    ════════════════════════════════════ */
    window.ftToggleCol = function (trigger) {
        const body = trigger.nextElementSibling;
        if (!body) return;
        const isOpen = body.classList.contains("is-open");
        body.classList.toggle("is-open", !isOpen);
        trigger.classList.toggle("is-open", !isOpen);
    };

    /* ════════════════════════════════════
       4. COPIAR EMAIL
    ════════════════════════════════════ */
    window.ftCopyEmail = function () {
        const btn = document.getElementById("ft-copy-email-btn");
        if (!btn) return;

        navigator.clipboard
            .writeText("info@orderrae.co")
            .then(function () {
                btn.classList.add("copied");
                btn.innerHTML = '<i class="fas fa-check"></i> ¡Copiado!';
                setTimeout(function () {
                    btn.classList.remove("copied");
                    btn.innerHTML = '<i class="fas fa-copy"></i> Copiar email';
                }, 2400);
            })
            .catch(function () {
                btn.innerHTML = '<i class="fas fa-times"></i> Error';
                setTimeout(function () {
                    btn.innerHTML = '<i class="fas fa-copy"></i> Copiar email';
                }, 1500);
            });
    };

    /* ════════════════════════════════════
       5. NEWSLETTER
    ════════════════════════════════════ */
    window.ftSuscribir = function () {
        const emailEl    = document.getElementById("ft-nl-email");
        const feedbackEl = document.getElementById("ft-nl-feedback");
        const btnEl      = document.getElementById("ft-nl-btn");
        const barEl      = document.getElementById("ft-nl-progress");
        const fillEl     = document.getElementById("ft-nl-progress-fill");
        if (!emailEl || !btnEl) return;

        const email  = emailEl.value.trim();
        const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

        /* Reset feedback */
        feedbackEl.className = "ft-nl-feedback";
        feedbackEl.textContent = "";

        if (!email || !emailOk) {
            feedbackEl.classList.add("error");
            feedbackEl.textContent = "Por favor ingresa un correo válido.";
            emailEl.focus();
            return;
        }

        /* Estado cargando */
        btnEl.textContent = "Enviando…";
        btnEl.disabled = true;
        barEl.classList.add("show");

        let prog = 0;
        const iv = setInterval(function () {
            prog = Math.min(prog + 6, 88);
            fillEl.style.width = prog + "%";
        }, 55);

        /*
         * ── REEMPLAZA ESTE setTimeout con tu fetch real ──
         *
         * fetch("/pagina/api/newsletter/suscribir/", {
         *     method: "POST",
         *     headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrf() },
         *     body: JSON.stringify({ email }),
         * })
         * .then(r => r.json())
         * .then(data => { if (!data.success) throw new Error(data.error); ftNlSuccess(); })
         * .catch(err => ftNlError(err.message));
         */
        setTimeout(function () {
            clearInterval(iv);
            fillEl.style.width = "100%";
            setTimeout(ftNlSuccess, 350);
        }, 1700);

        function ftNlSuccess() {
            barEl.classList.remove("show");
            fillEl.style.width = "0%";
            btnEl.textContent = "¡Suscrito! ✓";
            btnEl.classList.add("success");
            feedbackEl.classList.add("success");
            feedbackEl.textContent = "Revisa tu bandeja de entrada para confirmar.";
            emailEl.value = "";
            setTimeout(function () {
                btnEl.textContent = "Suscribirme →";
                btnEl.classList.remove("success");
                btnEl.disabled = false;
                feedbackEl.textContent = "";
                feedbackEl.className = "ft-nl-feedback";
            }, 4500);
        }

        function ftNlError(msg) {
            clearInterval(iv);
            barEl.classList.remove("show");
            fillEl.style.width = "0%";
            feedbackEl.classList.add("error");
            feedbackEl.textContent = msg || "Ocurrió un error. Intenta de nuevo.";
            btnEl.textContent = "Suscribirme →";
            btnEl.disabled = false;
        }
    };

    /* Enter en el input de newsletter */
    const nlInput = document.getElementById("ft-nl-email");
    if (nlInput) {
        nlInput.addEventListener("keydown", function (e) {
            if (e.key === "Enter") window.ftSuscribir();
        });
    }

    /* ════════════════════════════════════
       6. ANIMACIÓN DE ENTRADA (scroll)
    ════════════════════════════════════ */
    if ("IntersectionObserver" in window) {
        const io = new IntersectionObserver(
            function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("visible");
                        io.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.1 }
        );

        document
            .querySelectorAll(".footer-v2 .ft-animate")
            .forEach(function (el) { io.observe(el); });
    } else {
        /* Fallback sin soporte */
        document
            .querySelectorAll(".footer-v2 .ft-animate")
            .forEach(function (el) { el.classList.add("visible"); });
    }

    console.log("🪵 ORDER RAE Footer v2.0 — listo ✓");
})();