(function () {
  if (window.coreAllauthOnload) return;
  window.coreAllauthOnload = true;
  document.addEventListener("DOMContentLoaded", async function () {
    await window.coreUIReady;
    document.querySelectorAll("script[data-allauth-onload]").forEach(function (script) {
      const reference = script.dataset.allauthOnload;
      if (!reference || !reference.startsWith("allauth.")) return;
      const callback = reference.split(".").reduce(function (object, key) { return object && object[key]; }, window);
      if (typeof callback === "function") callback(JSON.parse(script.textContent));
    });
    document.querySelectorAll("[data-webauthn-pending]").forEach(function (button) { button.disabled = false; button.removeAttribute("data-webauthn-pending"); });
  });
})();
