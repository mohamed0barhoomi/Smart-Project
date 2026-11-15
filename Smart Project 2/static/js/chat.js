/* UML assistant: the interface is kept, but the chatbot is disabled in this version. */
(function () {
  "use strict";
  const sendForm = document.getElementById("chat-send-form");
  if (!sendForm) return;

  const input = document.getElementById("chat-input");
  const generateForm = document.getElementById("chat-form");
  const DISABLED = "The UML assistant is disabled in this version. Create the diagram manually.";

  sendForm.addEventListener("submit", (e) => {
    e.preventDefault();
    window.UI.toast(DISABLED, "info");
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendForm.requestSubmit(); }
  });
  generateForm.addEventListener("submit", (e) => {
    e.preventDefault();
    window.UI.toast(DISABLED, "info");
  });
})();
