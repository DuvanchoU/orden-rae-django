/* ================================================================
   ORDER RAE — header.js  v3.0
   Una sola línea · Sin buscador · Sin dark mode
================================================================ */

document.addEventListener("DOMContentLoaded", () => {

  const djData = (() => {
    try { return JSON.parse(document.getElementById("page-data")?.textContent || "{}"); }
    catch { return {}; }
  })();

  function getCsrf() {
    return document.cookie.split(";").reduce((v, c) => {
      const [k, val] = c.trim().split("=");
      return k === "csrftoken" ? decodeURIComponent(val) : v;
    }, "");
  }

  /* ════════════════════════════════════
     1. BARRA DE PROGRESO
  ════════════════════════════════════ */
  const progressFill = document.getElementById("page-progress-fill");

  function startProgress() {
    if (!progressFill) return;
    progressFill.style.transition = "none";
    progressFill.style.width = "0%";
    progressFill.classList.add("active");
    requestAnimationFrame(() => {
      progressFill.style.transition = "width 8s cubic-bezier(.1,1,.1,1)";
      progressFill.style.width = "85%";
    });
  }

  function finishProgress() {
    if (!progressFill) return;
    progressFill.classList.add("complete");
    progressFill.style.transition = "width 0.3s ease";
    progressFill.style.width = "100%";
    setTimeout(() => {
      progressFill.style.opacity = "0";
      setTimeout(() => {
        progressFill.classList.remove("active", "complete");
        progressFill.style.width = "0%";
        progressFill.style.opacity = "1";
        progressFill.style.transition = "";
      }, 300);
    }, 350);
  }

  document.querySelectorAll('a[href]').forEach(link => {
    const href = link.getAttribute('href');
    if (href && !href.startsWith('#') && !href.startsWith('javascript') && !href.startsWith('mailto')) {
      link.addEventListener('click', e => {
        if (!e.ctrlKey && !e.metaKey && !e.shiftKey) startProgress();
      });
    }
  });

  window.addEventListener('pageshow', finishProgress);
  window.addEventListener('load', finishProgress);
  window.showPageLoading  = startProgress;
  window.hidePageLoading  = finishProgress;

  /* ════════════════════════════════════
     2. SCROLL — compacto + ocultar mobile
  ════════════════════════════════════ */
  const header = document.getElementById("barra_superior");
  let lastScrollY = 0;
  let ticking = false;

  window.addEventListener("scroll", () => {
    if (!ticking) {
      requestAnimationFrame(() => {
        const y = window.scrollY;
        header?.classList.toggle("scrolled", y > 40);

        if (window.innerWidth < 768 && y > 100) {
          if (y > lastScrollY + 8)  header?.classList.add("hide-on-scroll");
          else if (y < lastScrollY - 4) header?.classList.remove("hide-on-scroll");
        } else {
          header?.classList.remove("hide-on-scroll");
        }

        lastScrollY = y;
        ticking = false;
      });
      ticking = true;
    }
  }, { passive: true });

  /* ════════════════════════════════════
     3. MENÚ USUARIO
  ════════════════════════════════════ */
  const menuUsuario = document.getElementById("menu-usuario");
  const avatarBtnEl = menuUsuario?.querySelector('.avatar-btn');

  window.toggleUserMenu = () => {
    const isOpen = menuUsuario?.classList.toggle("open");
    avatarBtnEl?.setAttribute("aria-expanded", isOpen ? "true" : "false");
    // Cerrar wishlist
    document.getElementById("wishlist-dropdown")?.classList.remove("open");
    document.getElementById("wishlist-btn")?.setAttribute("aria-expanded", "false");
  };

  document.addEventListener("click", e => {
    if (menuUsuario && !menuUsuario.contains(e.target)) {
      menuUsuario.classList.remove("open");
      avatarBtnEl?.setAttribute("aria-expanded", "false");
    }
  });

  /* ════════════════════════════════════
     4. WISHLIST DROPDOWN
  ════════════════════════════════════ */
  const wishlistBtn      = document.getElementById("wishlist-btn");
  const wishlistDropdown = document.getElementById("wishlist-dropdown");

  window.toggleWishlistDropdown = () => {
    const isOpen = wishlistDropdown?.classList.toggle("open");
    wishlistBtn?.classList.toggle("active", isOpen);
    wishlistBtn?.setAttribute("aria-expanded", isOpen ? "true" : "false");
    menuUsuario?.classList.remove("open");
    avatarBtnEl?.setAttribute("aria-expanded", "false");
  };

  document.addEventListener("click", e => {
    const wrap = document.getElementById("wishlist-wrap");
    if (wrap && !wrap.contains(e.target)) {
      wishlistDropdown?.classList.remove("open");
      wishlistBtn?.classList.remove("active");
      wishlistBtn?.setAttribute("aria-expanded", "false");
    }
  });

  /* ════════════════════════════════════
     5. CONTADOR CARRITO + PUNTO VERDE
  ════════════════════════════════════ */
  const contadorEl  = document.getElementById("contador-carrito");
  const cartNewDot  = document.getElementById("cart-new-dot");
  let dotTimeout;

  if (contadorEl) contadorEl.textContent = djData.carrito_cantidad ?? 0;

  window.updateCartCount = (n) => {
    if (!contadorEl) return;
    const prev = parseInt(contadorEl.textContent) || 0;
    contadorEl.textContent = n;

    contadorEl.classList.add("bump");
    setTimeout(() => contadorEl.classList.remove("bump"), 350);

    const carritoBtn = document.getElementById("carrito-btn");
    carritoBtn?.classList.add("cart-pop");
    setTimeout(() => carritoBtn?.classList.remove("cart-pop"), 400);

    if (n > prev && cartNewDot) {
      clearTimeout(dotTimeout);
      cartNewDot.classList.add("show");
      dotTimeout = setTimeout(() => cartNewDot.classList.remove("show"), 4000);
    }
  };

  /* ════════════════════════════════════
     6. MODAL AVATAR
  ════════════════════════════════════ */
  const avatarOverlay = document.getElementById("avatar-edit-overlay");
  const avatarPreview = document.getElementById("avatar-preview-img");
  const avatarFileIn  = document.getElementById("avatar-file-input");
  const avatarSaveBtn = document.getElementById("avatar-save-btn");
  const avatarLoading = document.getElementById("avatar-loading");
  const uploadBar     = document.getElementById("avatar-upload-bar");
  const uploadFill    = document.getElementById("avatar-upload-fill");
  let newAvatarFile   = null;

  window.openAvatarModal = () => {
    avatarOverlay?.classList.add("open");
    menuUsuario?.classList.remove("open");
    document.body.style.overflow = "hidden";
    newAvatarFile = null;
    if (avatarSaveBtn) avatarSaveBtn.disabled = true;
    if (uploadBar) uploadBar.classList.remove("show");
    if (uploadFill) uploadFill.style.width = "0%";
  };

  window.closeAvatarModal = () => {
    avatarOverlay?.classList.remove("open");
    document.body.style.overflow = "";
    const orig = document.getElementById("header-avatar")?.src;
    if (avatarPreview && orig) avatarPreview.src = orig;
    newAvatarFile = null;
    if (avatarSaveBtn) {
      avatarSaveBtn.disabled = true;
      avatarSaveBtn.innerHTML = '<i class="fas fa-check"></i> Guardar';
    }
  };

  avatarOverlay?.addEventListener("click", e => { if (e.target === avatarOverlay) window.closeAvatarModal(); });
  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && avatarOverlay?.classList.contains("open")) window.closeAvatarModal();
  });

  avatarFileIn?.addEventListener("change", e => {
    const file = e.target.files[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) { showHeaderToast("error", "Tipo inválido", "Solo JPG, PNG o WebP."); return; }
    if (file.size > 5 * 1024 * 1024)    { showHeaderToast("error", "Muy grande", "Máximo 5 MB."); return; }
    newAvatarFile = file;
    const reader = new FileReader();
    reader.onload = ev => { if (avatarPreview) avatarPreview.src = ev.target.result; };
    reader.readAsDataURL(file);
    if (avatarSaveBtn) avatarSaveBtn.disabled = false;
  });

  window.saveAvatar = async () => {
    if (!newAvatarFile) return;
    const formData = new FormData();
    formData.append("foto_perfil", newAvatarFile);
    formData.append("csrfmiddlewaretoken", getCsrf());

    if (avatarSaveBtn) { avatarSaveBtn.disabled = true; avatarSaveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Subiendo…'; }
    if (uploadBar) uploadBar.classList.add("show");
    if (avatarLoading) avatarLoading.classList.add("show");

    let prog = 0;
    const iv = setInterval(() => { prog = Math.min(prog + 8, 85); if (uploadFill) uploadFill.style.width = prog + "%"; }, 80);

    try {
      const res  = await fetch("/pagina/api/actualizar-avatar/", { method: "POST", body: formData, headers: { "X-CSRFToken": getCsrf() } });
      clearInterval(iv);
      if (uploadFill) uploadFill.style.width = "100%";
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      if (data.success) {
        const url = data.foto_url + "?v=" + Date.now();
        document.querySelectorAll("#header-avatar, #submenu-avatar, .avatar-img, .submenu-avatar-preview").forEach(img => img.src = url);
        if (avatarPreview) avatarPreview.src = url;
        showHeaderToast("success", "¡Foto actualizada!", "Tu nueva foto ya está lista.");
        setTimeout(() => window.closeAvatarModal(), 900);
      } else throw new Error(data.error || "No se pudo actualizar.");

    } catch (err) {
      clearInterval(iv);
      showHeaderToast("error", "Error al subir", err.message);
      if (avatarSaveBtn) { avatarSaveBtn.disabled = false; avatarSaveBtn.innerHTML = '<i class="fas fa-check"></i> Guardar'; }
    } finally {
      if (avatarLoading) avatarLoading.classList.remove("show");
      setTimeout(() => { if (uploadBar) uploadBar.classList.remove("show"); }, 600);
    }
  };

  /* ════════════════════════════════════
     7. SISTEMA DE TOASTS
  ════════════════════════════════════ */
  const toastQueue = [];
  let toastActive  = 0;
  const MAX_TOASTS = 3;

  function showHeaderToast(type, title, msg, duration = 4000) {
    if (toastActive >= MAX_TOASTS) { toastQueue.push({ type, title, msg, duration }); return; }

    let shelf = document.getElementById("toast-shelf");
    if (!shelf) {
      shelf = document.createElement("div");
      shelf.id = "toast-shelf";
      shelf.style.cssText = "position:fixed;bottom:2rem;right:2rem;z-index:9999;display:flex;flex-direction:column;gap:.5rem;pointer-events:none;max-width:340px;";
      document.body.appendChild(shelf);
    }

    const icons  = { success:"fa-check-circle", error:"fa-exclamation-circle", info:"fa-info-circle", warning:"fa-exclamation-triangle" };
    const colors = { success:"#06D6A0", error:"#EF476F", info:"#D4AF6F", warning:"#FFD166" };
    const c = colors[type] || colors.info;

    const el = document.createElement("div");
    el.setAttribute("role", "alert");
    el.style.cssText = `background:#fff;border-radius:14px;padding:.82rem 1rem;display:flex;align-items:center;gap:.65rem;box-shadow:0 8px 32px rgba(139,94,60,.18);pointer-events:auto;animation:tIn .3s cubic-bezier(.16,1,.3,1);border-left:3.5px solid ${c};cursor:pointer;`;
    el.innerHTML = `<i class="fas ${icons[type]||icons.info}" style="color:${c};font-size:1rem;flex-shrink:0;"></i><div style="flex:1;min-width:0;"><div style="font-weight:700;font-size:.86rem;color:#1C1510;">${title}</div>${msg?`<div style="font-size:.75rem;color:#9B8878;margin-top:1px;">${msg}</div>`:""}</div><button onclick="this.parentElement.remove()" aria-label="Cerrar" style="background:none;border:none;cursor:pointer;color:#9B8878;font-size:.76rem;padding:2px;flex-shrink:0;">✕</button>`;

    shelf.appendChild(el);
    toastActive++;

    const dismiss = () => {
      el.style.transition = "opacity .25s,transform .25s";
      el.style.opacity = "0";
      el.style.transform = "translateX(24px)";
      setTimeout(() => {
        el.remove();
        toastActive = Math.max(0, toastActive - 1);
        if (toastQueue.length > 0) { const next = toastQueue.shift(); showHeaderToast(next.type, next.title, next.msg, next.duration); }
      }, 260);
    };

    el.addEventListener("click", e => { if (!e.target.closest("button")) dismiss(); });
    setTimeout(dismiss, duration);
  }

  window.showToast = showHeaderToast;

  /* ════════════════════════════════════
     8. API CARRITO (global)
  ════════════════════════════════════ */
  window.addToCart = async (id, nombre, precio, btnEl) => {
    const orig = btnEl?.innerHTML;
    if (btnEl) { btnEl.innerHTML = '<span class="spinner-border spinner-border-sm" style="width:13px;height:13px"></span>'; btnEl.disabled = true; }

    try {
      const res  = await fetch("/pagina/api/carrito/agregar/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrf() },
        body: JSON.stringify({ producto_id: id, cantidad: 1, precio, nombre }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      if (data.success) {
        window.updateCartCount(data.cantidad_total);
        showHeaderToast("success", "¡Añadido!", `${nombre} está en tu carrito.`);
        if (btnEl) {
          btnEl.innerHTML = '<i class="fas fa-check me-1"></i> ¡Añadido!';
          btnEl.classList.add("added");
          setTimeout(() => { btnEl.innerHTML = orig; btnEl.classList.remove("added"); btnEl.disabled = false; }, 2400);
        }
      } else throw new Error(data.error || "No se pudo añadir");

    } catch (err) {
      showHeaderToast("error", "Error", err.message);
      if (btnEl) { btnEl.innerHTML = orig; btnEl.disabled = false; }
    }
  };

  /* ════════════════════════════════════
     9. API WISHLIST (global)
  ════════════════════════════════════ */
  window.toggleWishlist = async (productoId, btnEl) => {
    try {
      const res  = await fetch("/pagina/api/wishlist/toggle/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrf() },
        body: JSON.stringify({ producto_id: productoId }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      if (data.success) {
        const count  = data.cantidad_total ?? 0;
        const badge  = document.getElementById("wishlist-count");
        const heartBtn = document.getElementById("wishlist-btn");

        if (badge) { badge.textContent = count; badge.classList.add("bump"); setTimeout(() => badge.classList.remove("bump"), 350); }

        if (data.accion === "agregado") {
          heartBtn?.classList.add("has-items");
          showHeaderToast("success", "Guardado", "Añadido a favoritos.");
          if (btnEl) btnEl.style.color = "var(--h-accent)";
        } else {
          if (count === 0) heartBtn?.classList.remove("has-items");
          showHeaderToast("info", "Eliminado", "Quitado de favoritos.");
          if (btnEl) btnEl.style.color = "";
        }
      }
    } catch { showHeaderToast("error", "Error", "No se pudo actualizar favoritos."); }
  };

  console.log("🪵 ORDER RAE Header v3.0 — listo ✓");
});

/* Animación toast */
if (!document.getElementById("rae-toast-anim")) {
  const s = document.createElement("style");
  s.id = "rae-toast-anim";
  s.textContent = `@keyframes tIn{from{opacity:0;transform:translateX(40px) scale(.95)}to{opacity:1;transform:translateX(0) scale(1)}}`;
  document.head.appendChild(s);
}