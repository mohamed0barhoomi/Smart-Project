/*
 * Shared UI behaviours: toasts, dropdown menus, confirmation dialog,
 * rename dialog, auto-submitting filters, mobile sidebar.
 * Exposed as window.UI so the editor reuses the same components.
 */
(function () {
  "use strict";

  const ICONS = { success: "check", info: "info", error: "alert", warning: "alert" };

  // ---------------- toasts ----------------
  function bindToast(el) {
    const close = () => {
      el.classList.add("leaving");
      setTimeout(() => el.remove(), 200);
    };
    el.querySelector(".toast-close")?.addEventListener("click", close);
    if (el.hasAttribute("data-autohide")) setTimeout(close, 4500);
  }

  function toast(message, type = "success") {
    const box = document.getElementById("toasts");
    const el = document.createElement("div");
    el.className = `toast toast-${type}`;
    el.setAttribute("data-autohide", "");
    el.innerHTML = `<svg class="icon"><use href="#i-${ICONS[type] || "info"}"></use></svg>
      <span></span>
      <button type="button" class="toast-close" aria-label="Close"><svg class="icon"><use href="#i-x"></use></svg></button>`;
    el.querySelector("span").textContent = message;
    box.appendChild(el);
    bindToast(el);
  }

  // ---------------- modals ----------------
  let lastFocus = null;

  function openModal(modal) {
    lastFocus = document.activeElement;
    modal.hidden = false;
    void modal.offsetWidth;            // force a reflow so the CSS transition runs
    modal.classList.add("open");
    const focusable = modal.querySelector("input, textarea, button[type=submit]");
    setTimeout(() => focusable?.focus(), 30);
  }

  function closeModal(modal) {
    modal.classList.remove("open");
    setTimeout(() => { modal.hidden = true; }, 150);
    lastFocus?.focus?.();
  }

  /**
   * Show the confirmation dialog.
   * - with `url`: the dialog's form is POSTed to that url;
   * - with `onConfirm`: the callback is called instead (used by the editor).
   */
  function confirmDialog({ title = "Are you sure?", text = "", confirmLabel = "Delete", url = null, onConfirm = null }) {
    const modal = document.getElementById("confirm-modal");
    const form = document.getElementById("confirm-form");
    modal.querySelector("#confirm-title").textContent = title;
    modal.querySelector("#confirm-text").textContent = text;
    modal.querySelector("#confirm-submit").textContent = confirmLabel;
    form.action = url || "";
    form.onsubmit = onConfirm ? (e) => { e.preventDefault(); closeModal(modal); onConfirm(); } : null;
    openModal(modal);
  }

  document.addEventListener("click", (e) => {
    if (e.target.closest("[data-close]")) {
      const modal = e.target.closest(".modal");
      if (modal) closeModal(modal);
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    const open = document.querySelector(".modal.open");
    if (open) { closeModal(open); e.stopPropagation(); }
    closeMenus();
  }, true);

  // ---------------- dropdown menus ----------------
  function closeMenus(except) {
    document.querySelectorAll(".dropdown.open").forEach((d) => { if (d !== except) d.classList.remove("open"); });
  }

  document.addEventListener("click", (e) => {
    const trigger = e.target.closest("[data-dropdown]");
    if (trigger) {
      const dropdown = trigger.closest(".dropdown");
      closeMenus(dropdown);
      dropdown.classList.toggle("open");
      e.stopPropagation();
      return;
    }
    if (!e.target.closest(".menu")) closeMenus();
    else if (e.target.closest("[role=menuitem]")) closeMenus();
  });

  // ---------------- data-confirm / data-rename buttons ----------------
  document.addEventListener("click", (e) => {
    const del = e.target.closest("[data-confirm-url]");
    if (del) {
      confirmDialog({ title: del.dataset.confirmTitle || "Are you sure?", text: del.dataset.confirmText, url: del.dataset.confirmUrl });
      return;
    }
    const rename = e.target.closest("[data-rename-url]");
    if (rename) {
      const modal = document.getElementById("rename-modal");
      const field = rename.dataset.renameField || "name";
      modal.querySelector("#rename-form").action = rename.dataset.renameUrl;
      modal.querySelector("#rename-title").textContent = rename.dataset.renameHeading || "Edit";
      modal.querySelector("#rename-label").textContent = field === "title" ? "Title" : "Name";
      modal.querySelector("#rename-input-title").name = field;
      modal.querySelector("#rename-input-title").value = rename.dataset.title || "";
      modal.querySelector("#rename-input-description").value = rename.dataset.description || "";
      openModal(modal);
    }
  });

  // ---------------- filters: submit on change, debounce search ----------------
  const filters = document.getElementById("filters");
  if (filters) {
    let timer;
    filters.addEventListener("change", () => filters.submit());
    filters.querySelector("input[type=search]")?.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(() => filters.submit(), 450);
    });
    // keep the cursor at the end of the search box after reload
    const search = filters.querySelector("input[type=search]");
    if (search && search.value) { search.focus(); search.setSelectionRange(search.value.length, search.value.length); }
  }

  // ---------------- mobile sidebar ----------------
  document.addEventListener("click", (e) => {
    if (e.target.closest("[data-toggle-sidebar]")) document.body.classList.toggle("sidebar-open");
    else if (document.body.classList.contains("sidebar-open") && !e.target.closest(".sidebar")) document.body.classList.remove("sidebar-open");
  });

  // ---------------- generic "open this modal" buttons ----------------
  document.addEventListener("click", (e) => {
    const opener = e.target.closest("[data-open-modal]");
    if (opener) openModal(document.getElementById(opener.dataset.openModal));
  });
  // re-open the create-project dialog when the server sent back validation errors
  document.querySelectorAll(".modal .field.has-error").forEach((field) => openModal(field.closest(".modal")));

  // ---------------- project workspace ----------------
  const diagramModal = document.getElementById("diagram-modal");
  const chatForm = document.getElementById("chat-form");
  const TYPE_LABELS = { class: "class diagram", usecase: "use case diagram" };

  document.addEventListener("click", (e) => {
    const manual = e.target.closest("[data-new-diagram]");
    if (manual && diagramModal) {
      const type = manual.dataset.newDiagram;
      diagramModal.querySelector("#diagram-modal-type").value = type;
      diagramModal.querySelector("#diagram-modal-title").textContent = `New ${TYPE_LABELS[type]}`;
      openModal(diagramModal);
      return;
    }
    const generate = e.target.closest("[data-generate-type]");
    if (generate && chatForm) {
      const radio = chatForm.querySelector(`input[name="diagram_type"][value="${generate.dataset.generateType}"]`);
      if (radio) radio.checked = true;
      document.getElementById("chatbot").scrollIntoView({ behavior: "smooth", block: "start" });
      setTimeout(() => document.getElementById("chat-input").focus({ preventScroll: true }), 350);
      return;
    }
    const example = e.target.closest("[data-example]");
    if (example && chatForm) {
      const input = document.getElementById("chat-input");
      input.value = example.dataset.example;
      input.dispatchEvent(new Event("input"));
      input.focus();
    }
  });

  // the conversation itself (send, generate) is handled by static/js/chat.js

  document.querySelectorAll(".toast").forEach(bindToast);

  window.UI = { toast, confirm: confirmDialog, openModal, closeModal };
})();
