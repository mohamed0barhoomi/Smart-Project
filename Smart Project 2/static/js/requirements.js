/* Requirements section: tabs, inline priority change, UML generation from the requirements. */
(function () {
  "use strict";
  const section = document.getElementById("requirements");
  if (!section) return;

  // tabs (the server also opens the right tab with ?req=...)
  section.querySelectorAll("[data-req-tab]").forEach((tab) => {
    tab.addEventListener("click", () => {
      section.querySelectorAll("[data-req-tab]").forEach((t) => t.classList.toggle("active", t === tab));
      section.querySelectorAll("[data-req-panel]").forEach((panel) => {
        panel.hidden = panel.dataset.reqPanel !== tab.dataset.reqTab;
      });
      const url = new URL(location.href);
      url.searchParams.set("req", tab.dataset.reqTab);
      history.replaceState(null, "", url.pathname + url.search + "#requirements");
    });
  });

  // priority: saved as soon as it changes
  section.querySelectorAll("select[data-auto-submit]").forEach((select) => {
    select.addEventListener("change", () => select.form.submit());
  });

  // UML from requirements: uses the chatbot, which is disabled in this version
  const uml = document.getElementById("req-uml-form");
  uml?.addEventListener("submit", (e) => {
    e.preventDefault();
    window.UI.toast("The UML assistant is disabled in this version. Create the diagram manually.", "info");
  });
})();
