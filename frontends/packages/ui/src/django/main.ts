import { createApp, h, nextTick } from "vue";
import { KeyRound, Send, Mail, ArrowRight, ShieldCheck, UserRound, Monitor, LockKeyhole } from "@lucide/vue";
import { Button } from "@dnk/ui/components/button";
import { Badge } from "@dnk/ui/components/badge";
import { Alert, AlertDescription } from "@dnk/ui/components/alert";
import { Avatar, AvatarFallback } from "@dnk/ui/components/avatar";
import { Spinner } from "@dnk/ui/components/spinner";
import { Separator } from "@dnk/ui/components/separator";
import FieldControl from "./FieldControl.vue";
import AccountMenu from "./AccountMenu.vue";
import LoginChannels from "./LoginChannels.vue";
import type { FieldSchema } from "./types";
import "../style.css";

const icons = { key: KeyRound, telegram: Send, email: Mail, arrow: ArrowRight, shield: ShieldCheck, user: UserRound, monitor: Monitor, lock: LockKeyhole };

function mountField(host: HTMLElement) {
  const script = host.querySelector<HTMLScriptElement>('script[type="application/json"]');
  const fallback = host.querySelector<HTMLElement>("[data-field-fallback]") ?? host;
  const input = fallback.querySelector<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>("input:not([type=hidden]), textarea, select");
  if (!input) return;
  const schema: FieldSchema = script ? JSON.parse(script.textContent ?? "{}") : {
    type: input instanceof HTMLTextAreaElement ? "textarea" : input.type,
    attrs: Object.fromEntries(Array.from(input.attributes, attr => [attr.name, attr.value])),
    label: fallback.querySelector("label")?.textContent?.trim() ?? "",
    help: fallback.querySelector(".helptext")?.textContent?.trim() ?? "",
    errors: Array.from(fallback.querySelectorAll(".errorlist li"), item => item.textContent ?? ""),
    value: "", options: [],
  };
  if (schema.type === "radio") return; // grouped server fields are enhanced together below.
  schema.value = schema.type === "radio-group" ? (fallback.querySelector<HTMLInputElement>("input:checked")?.value ?? "") : input.value;
  if (input instanceof HTMLInputElement && input.type === "checkbox") {
    schema.checked = input.checked;
    schema.checkboxValue = input.value;
  }
  for (const flag of ["required", "disabled", "readonly", "autofocus"]) {
    if (input.hasAttribute(flag)) schema.attrs[flag] = true;
    else delete schema.attrs[flag];
  }
  delete schema.attrs.value;
  delete schema.attrs.class;
  // A mixed MFA code also accepts recovery codes. Never truncate it to six.
  if (input.name === "code" && !/\/2fa\//.test(location.pathname)) schema.type = "otp";
  const focused = document.activeElement === input;
  const start = input instanceof HTMLInputElement && ["text", "password", "tel"].includes(input.type) ? input.selectionStart : null;
  const end = input instanceof HTMLInputElement && ["text", "password", "tel"].includes(input.type) ? input.selectionEnd : null;
  const app = createApp(FieldControl, { field: schema });
  app.mount(host);
  host.classList.remove("native-field");
  if (focused) void nextTick(() => {
    const control = document.getElementById(String(schema.attrs.id));
    control?.focus();
    if (control instanceof HTMLInputElement && start !== null && end !== null) control.setSelectionRange(start, end);
  });
}

function enhanceButtons() {
  document.querySelectorAll<HTMLElement>(".button, [data-ui-button]").forEach(old => {
    if (old.closest("[data-v-app]")) return;
    const attrs = Object.fromEntries(Array.from(old.attributes, attr => [attr.name, attr.value]));
    const label = old.textContent?.trim() ?? "";
    const iconName = old.dataset.icon as keyof typeof icons | undefined;
    const icon = iconName && icons[iconName];
    const variant = old.classList.contains("button-danger") ? "destructive" : old.classList.contains("button-outline") ? "outline" : old.classList.contains("button-link") ? "link" : "default";
    delete attrs.class;
    const host = document.createElement("span");
    host.className = "button-island";
    old.replaceWith(host);
    createApp({ render: () => h(Button, { ...attrs, as: old.tagName.toLowerCase(), variant }, () => [h(Spinner, { class: "core-button-spinner", "aria-hidden": true }), icon && h(icon), label]) }).mount(host);
  });
}

function submissionState() {
  const reset = () => {
    document.querySelectorAll<HTMLFormElement>("form[data-submitting]").forEach(form => delete form.dataset.submitting);
    document.querySelectorAll<HTMLButtonElement>('button[data-core-busy]').forEach(button => {
      button.disabled = false; button.removeAttribute("aria-busy"); delete button.dataset.coreBusy;
    });
  };
  const busy = (button: HTMLButtonElement) => {
    button.dataset.coreBusy = "true";
    button.setAttribute("aria-busy", "true");
    // Defer disabling until native submission has collected the submitter value.
    setTimeout(() => { if (button.dataset.coreBusy) button.disabled = true; }, 0);
  };
  document.addEventListener("submit", event => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    const ceremonyButton = form.querySelector<HTMLButtonElement>("#mfa_webauthn_signup, #mfa_webauthn_add, #mfa_webauthn_authenticate, #mfa_webauthn_reauthenticate");
    if (ceremonyButton && !form.querySelector<HTMLInputElement>('input[name="credential"]')?.value) {
      event.preventDefault(); ceremonyButton.click(); return;
    }
    if (form.dataset.submitting) { event.preventDefault(); return; }
    // allauth intercepts passkey login itself; only regular forms use this guard.
    if (form.id === "mfa_login") return;
    form.dataset.submitting = "true";
    if (event.submitter instanceof HTMLButtonElement) busy(event.submitter);
    setTimeout(reset, 15000);
  });
  document.addEventListener("click", event => {
    const button = event.target instanceof Element ? event.target.closest<HTMLButtonElement>("button") : null;
    if (!button || !["passkey_login", "mfa_webauthn_signup", "mfa_webauthn_add", "mfa_webauthn_authenticate", "mfa_webauthn_reauthenticate"].includes(button.id)) return;
    if (button.dataset.coreBusy) { event.preventDefault(); event.stopImmediatePropagation(); return; }
    busy(button);
  }, true);
  window.addEventListener("pageshow", reset);
  document.addEventListener("allauth.error", reset);
}

function enhance() {
  if (window.coreUIState === "fallback") return;
  try {
    // Allauth also emits individual radio elements (email selection). Combine
    // each named group so keyboard navigation and native submission stay intact.
    document.querySelectorAll<HTMLFormElement>("form").forEach(form => {
      const groups = new Map<string, HTMLInputElement[]>();
      form.querySelectorAll<HTMLInputElement>('input[type="radio"]').forEach(input => {
        if (!input.closest("[data-core-field]")?.querySelector('script[type="application/json"]')) groups.set(input.name, [...(groups.get(input.name) ?? []), input]);
      });
      groups.forEach((inputs, name) => {
        const host = inputs[0]?.closest<HTMLElement>("[data-core-field]");
        if (!host) return;
        const options = inputs.map(input => ({ value: input.value, label: form.querySelector(`label[for="${CSS.escape(input.id)}"]`)?.textContent?.trim() ?? input.value }));
        const schema: FieldSchema = { type: "radio-group", attrs: { id: `id_${name}`, name }, label: name === "email" ? "Выберите email" : "Выберите аккаунт", value: inputs.find(input => input.checked)?.value ?? "", help: "", errors: [], options };
        inputs.slice(1).forEach(input => { const row = input.closest("[data-core-field]"); if (row && row !== host) row.remove(); });
        createApp(FieldControl, { field: schema }).mount(host);
        host.removeAttribute("data-core-field"); host.classList.remove("native-field");
      });
    });
    document.querySelectorAll<HTMLElement>("[data-core-field]").forEach(mountField);
    document.querySelectorAll<HTMLElement>("[data-channel-selector]").forEach(host => {
      const links = Array.from(host.querySelectorAll<HTMLAnchorElement>("a[data-channel]"));
      const channels = links.map(link => ({ value: link.dataset.channel!, label: link.textContent!.trim(), href: link.href, panelId: link.getAttribute("aria-controls")! }));
      const initial = links.find(link => link.hasAttribute("aria-current"))!.dataset.channel!;
      const focused = links.find(link => link === document.activeElement)?.dataset.channel;
      createApp(LoginChannels, { channels, initial, focused }).mount(host);
    });
    document.querySelectorAll<HTMLElement>("[data-ui-alert]").forEach(host => {
      const text = host.textContent?.trim();
      createApp({ render: () => h(Alert, { variant: host.classList.contains("form-errors") ? "destructive" : "default" }, () => h(AlertDescription, () => text)) }).mount(host);
    });
    document.querySelectorAll<HTMLElement>("[data-ui-badge]").forEach(host => {
      const text = host.textContent?.trim();
      createApp({ render: () => h(Badge, { variant: "secondary" }, () => text) }).mount(host);
    });
    document.querySelectorAll<HTMLElement>("[data-ui-avatar]").forEach(host => {
      const text = host.textContent?.trim();
      createApp({ render: () => h(Avatar, { class: "size-12" }, () => h(AvatarFallback, () => text)) }).mount(host);
    });
    document.querySelectorAll<HTMLElement>("[data-ui-separator]").forEach(host => createApp(Separator).mount(host));
    document.querySelectorAll<HTMLElement>("[data-ui-icon]").forEach(host => {
      const icon = icons[host.dataset.uiIcon as keyof typeof icons];
      if (icon) createApp({ render: () => h(icon, { "aria-hidden": true }) }).mount(host);
    });
    enhanceButtons();
    const navigation = document.querySelector<HTMLElement>(".account-navigation");
    if (navigation) {
      const links = Array.from(navigation.querySelectorAll<HTMLAnchorElement>("a"), a => ({ href: a.href, text: a.textContent?.trim() ?? "", current: a.hasAttribute("aria-current") }));
      const mobile = document.createElement("div"); mobile.className = "account-mobile-menu";
      navigation.before(mobile);
      createApp(AccountMenu, { links }).mount(mobile);
      navigation.classList.add("has-mobile-menu");
    }
    submissionState();
  } finally {
    window.coreUIState = "ready";
    window.resolveCoreUI?.();
    document.dispatchEvent(new Event("core:ui-ready"));
  }
}
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", enhance, { once: true });
else enhance();
