(function () {
  const actionIds = new Set([
    "passkey_login",
    "mfa_webauthn_add",
    "mfa_webauthn_signup",
    "mfa_webauthn_authenticate",
    "mfa_webauthn_reauthenticate",
  ]);
  const feedback = document.getElementById("webauthn-feedback");
  if (!feedback) return;

  document.addEventListener("allauth.error", function (event) {
    const tags = event.detail?.tags;
    if (!Array.isArray(tags) || !tags.includes("mfa") || !tags.includes("webauthn")) return;
    event.preventDefault();
    const name = event.detail?.exception?.name;
    feedback.textContent = name === "AbortError" || name === "NotAllowedError"
      ? "Действие с passkey отменено или не подтверждено. Попробуйте ещё раз."
      : "Не удалось выполнить проверку passkey. Проверьте соединение и попробуйте ещё раз.";
    feedback.hidden = false;
  });

  document.addEventListener("click", function (event) {
    const button = event.target instanceof Element ? event.target.closest("button") : null;
    if (button && actionIds.has(button.id)) feedback.hidden = true;
  }, true);
})();
