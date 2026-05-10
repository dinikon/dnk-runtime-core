<script setup lang="ts">
import {computed, nextTick, onMounted, ref} from "vue";
import {useRouter} from "vue-router";

import {useSessionStore} from "@/app/stores/session";

const router = useRouter();
const sessionStore = useSessionStore();

const email = ref("");
const codeDigits = ref(["", "", "", "", "", ""]);
const codeInputs = ref<HTMLInputElement[]>([]);

const loginStep = computed(() => {
  if (sessionStore.isResolvingTenant || !sessionStore.tenant) {
    return "checking";
  }

  if (!sessionStore.isTenantAvailable) {
    return "workspace-not-found";
  }

  return sessionStore.emailChallenge ? "otp" : "email";
});

const code = computed(() => codeDigits.value.join(""));
const canRequestOtp = computed(() => email.value.trim().length > 3 && !sessionStore.isRequestingOtp);
const canConfirmOtp = computed(() => code.value.length === 6 && !sessionStore.isConfirmingOtp);

onMounted(() => {
  void sessionStore.resolveTenant();
});

async function requestOtp() {
  if (!canRequestOtp.value) {
    return;
  }

  try {
    await sessionStore.requestEmailOtp(email.value.trim());
  } catch {
    return;
  }

  codeDigits.value = ["", "", "", "", "", ""];
  await nextTick();
  codeInputs.value[0]?.focus();
}

async function confirmOtp() {
  if (!canConfirmOtp.value) {
    return;
  }

  try {
    await sessionStore.confirmEmailOtp(code.value);
  } catch {
    return;
  }

  await router.push("/");
}

function updateCodeDigit(index: number, event: Event) {
  const input = event.target as HTMLInputElement;
  const digits = input.value.replace(/\D/g, "").slice(0, 6).split("");

  if (digits.length > 1) {
    codeDigits.value = codeDigits.value.map((digit, digitIndex) => digits[digitIndex] ?? digit);
    codeInputs.value[Math.min(digits.length, codeInputs.value.length - 1)]?.focus();
    return;
  }

  codeDigits.value[index] = digits[0] ?? "";

  if (digits[0] && index < codeInputs.value.length - 1) {
    codeInputs.value[index + 1]?.focus();
  }
}

function moveCodeFocus(index: number, event: KeyboardEvent) {
  if (event.key === "Backspace" && !codeDigits.value[index] && index > 0) {
    codeInputs.value[index - 1]?.focus();
  }
}

function openMail(provider: "gmail" | "outlook") {
  const href =
      provider === "gmail"
          ? "https://mail.google.com/mail/u/0/#inbox"
          : "https://outlook.live.com/mail/0/inbox";

  window.open(href, "_blank", "noopener,noreferrer");
}
</script>

<template>
  <section class="auth-page">
    <div v-if="loginStep === 'checking'" class="auth-card auth-card--compact">
      <div class="auth-spinner" aria-hidden="true"></div>
      <h1>Loading workspace</h1>
      <p>Checking the current workspace address.</p>
    </div>

    <div v-else-if="loginStep === 'workspace-not-found'" class="auth-card auth-card--compact">
      <h1>Вітаємо в dNiko</h1>
      <p>Робочий простір за цією адресою не знайдено або він недоступний.</p>
      <p class="auth-legal">
        By using dNiko, you agree to the Terms of Service and Data Processing Agreement.
      </p>
    </div>

    <form v-else-if="loginStep === 'email'" class="auth-card" @submit.prevent="requestOtp">
      <h1>Welcome to dNiko</h1>

      <button class="auth-provider-button" type="button" disabled>
        <span class="provider-mark provider-mark--google">G</span>
        Continue with Google
      </button>
      <button class="auth-provider-button" type="button" disabled>
        <span class="provider-mark provider-mark--microsoft">M</span>
        Continue with Microsoft
      </button>

      <input
          v-model="email"
          class="auth-input"
          type="email"
          autocomplete="email"
          placeholder="tim@apple.dev"
          required
      />

      <button class="auth-primary-button" type="submit" :disabled="!canRequestOtp">
        {{ sessionStore.isRequestingOtp ? "Sending..." : "Continue" }}
      </button>

      <p v-if="sessionStore.authError" class="auth-error">{{ sessionStore.authError }}</p>
      <p class="auth-legal">
        By using dNiko, you agree to the Terms of Service and Data Processing Agreement.
      </p>
    </form>

    <form v-else class="auth-card auth-card--otp" @submit.prevent="confirmOtp">
      <div class="auth-icon" aria-hidden="true">✉</div>
      <h1>Check your Emails</h1>
      <p>
        A verification email has been sent to:<br/>
        <strong>{{ sessionStore.emailChallenge?.email }}</strong>
      </p>

      <button class="auth-mail-button" type="button" @click="openMail('gmail')">
        <span class="provider-mark provider-mark--google">G</span>
        Open Gmail
      </button>
      <button class="auth-mail-button" type="button" @click="openMail('outlook')">
        <span class="provider-mark provider-mark--microsoft">M</span>
        Open Outlook
      </button>

      <div class="otp-inputs" aria-label="Verification code">
        <input
            v-for="(_, index) in codeDigits"
            :key="index"
            ref="codeInputs"
            :value="codeDigits[index]"
            class="otp-input"
            inputmode="numeric"
            maxlength="6"
            autocomplete="one-time-code"
            @input="updateCodeDigit(index, $event)"
            @keydown="moveCodeFocus(index, $event)"
        />
      </div>

      <p v-if="sessionStore.emailChallenge?.devCode" class="auth-dev-code">
        Development code: {{ sessionStore.emailChallenge.devCode }}
      </p>

      <button class="auth-primary-button" type="submit" :disabled="!canConfirmOtp">
        {{ sessionStore.isConfirmingOtp ? "Checking..." : "Continue" }}
      </button>

      <p v-if="sessionStore.authError" class="auth-error">{{ sessionStore.authError }}</p>

      <div class="auth-footer-actions">
        <button type="button" @click="requestOtp">Resend email</button>
        <button type="button" @click="sessionStore.emailChallenge = null">Change email</button>
      </div>
    </form>
  </section>
</template>
