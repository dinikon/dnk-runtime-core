<script setup lang="ts">
import {computed, onMounted, ref} from "vue";
import {useRouter} from "vue-router";

import {useSessionStore} from "@/app/stores/session";
import {AuthCard, AuthProviderButton, AuthShell, OtpCodeInput} from "@/features/auth/components";

const router = useRouter();
const sessionStore = useSessionStore();

const email = ref("");
const code = ref("");

const loginStep = computed(() => {
  if (sessionStore.isResolvingTenant || !sessionStore.tenant) {
    return "checking";
  }

  if (!sessionStore.isTenantAvailable) {
    return "workspace-not-found";
  }

  return sessionStore.emailChallenge ? "otp" : "email";
});

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

  code.value = "";
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

function openMail(provider: "gmail" | "outlook") {
  const href =
      provider === "gmail"
          ? "https://mail.google.com/mail/u/0/#inbox"
          : "https://outlook.live.com/mail/0/inbox";

  window.open(href, "_blank", "noopener,noreferrer");
}
</script>

<template>
  <AuthShell>
    <AuthCard v-if="loginStep === 'checking'" class="min-h-42 max-w-80 content-center gap-3.5">
      <div
          class="mx-auto size-5.5 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"
          aria-hidden="true"
      />
      <h1 class="text-sm font-semibold leading-tight">Loading workspace</h1>
      <p class="text-[0.7rem] leading-relaxed text-neutral-500">Checking the current workspace address.</p>
    </AuthCard>

    <AuthCard v-else-if="loginStep === 'workspace-not-found'" class="min-h-42 max-w-80 content-center gap-3.5">
      <h1 class="text-sm font-semibold leading-tight">Вітаємо в dNiko</h1>
      <p class="text-[0.7rem] leading-relaxed text-neutral-500">
        Робочий простір за цією адресою не знайдено або він недоступний.
      </p>
      <p class="mt-2 px-1 text-[0.66rem] leading-relaxed text-neutral-400">
        By using dNiko, you agree to the Terms of Service and Data Processing Agreement.
      </p>
    </AuthCard>

    <AuthCard v-else-if="loginStep === 'email'">
      <form class="grid gap-2.5" @submit.prevent="requestOtp">
        <h1 class="mb-2 text-sm font-semibold leading-tight">Welcome to dNiko</h1>

        <AuthProviderButton provider="google" disabled>
          Continue with Google
        </AuthProviderButton>
        <AuthProviderButton provider="microsoft" disabled>
          Continue with Microsoft
        </AuthProviderButton>

        <input
            v-model="email"
            class="min-h-8 w-full rounded border border-neutral-200 bg-white px-3 text-center text-xs text-neutral-900 outline-none transition-colors placeholder:text-neutral-400 focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
            type="email"
            autocomplete="email"
            placeholder="tim@apple.dev"
            required
        />

        <button
            class="inline-flex min-h-7 w-full items-center justify-center rounded bg-neutral-900 text-[0.72rem] font-semibold text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:bg-neutral-400"
            type="submit"
            :disabled="!canRequestOtp"
        >
          {{ sessionStore.isRequestingOtp ? "Sending..." : "Continue" }}
        </button>

        <p v-if="sessionStore.authError" class="text-[0.7rem] font-semibold leading-relaxed text-red-700">
          {{ sessionStore.authError }}
        </p>
        <p class="mt-2 px-1 text-[0.66rem] leading-relaxed text-neutral-500">
          By using dNiko, you agree to the Terms of Service and Data Processing Agreement.
        </p>
      </form>
    </AuthCard>

    <AuthCard v-else class="max-w-[308px] pt-7">
      <form class="grid gap-2.5" @submit.prevent="confirmOtp">
        <div
            class="mx-auto grid size-7.5 place-items-center rounded-full border border-neutral-900 text-sm text-neutral-900"
            aria-hidden="true"
        >
          ✉
        </div>
        <h1 class="text-sm font-semibold leading-tight">Check your Emails</h1>
        <p class="text-[0.7rem] leading-relaxed text-neutral-500">
          A verification email has been sent to:<br/>
          <strong>{{ sessionStore.emailChallenge?.email }}</strong>
        </p>

        <AuthProviderButton provider="google" variant="outline" @click="openMail('gmail')">
          Open Gmail
        </AuthProviderButton>
        <AuthProviderButton provider="microsoft" variant="outline" @click="openMail('outlook')">
          Open Outlook
        </AuthProviderButton>

        <OtpCodeInput v-model="code" class="my-1"/>

        <p
            v-if="sessionStore.emailChallenge?.devCode"
            class="text-[0.7rem] font-semibold leading-relaxed text-neutral-700"
        >
          Development code: {{ sessionStore.emailChallenge.devCode }}
        </p>

        <button
            class="inline-flex min-h-7 w-full items-center justify-center rounded bg-neutral-900 text-[0.72rem] font-semibold text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:bg-neutral-400"
            type="submit"
            :disabled="!canConfirmOtp"
        >
          {{ sessionStore.isConfirmingOtp ? "Checking..." : "Continue" }}
        </button>

        <p v-if="sessionStore.authError" class="text-[0.7rem] font-semibold leading-relaxed text-red-700">
          {{ sessionStore.authError }}
        </p>

        <div class="mt-1 flex justify-center gap-3.5">
          <button class="text-[0.66rem] font-medium text-neutral-400 hover:text-neutral-700" type="button"
                  @click="requestOtp">
            Resend email
          </button>
          <button
              class="text-[0.66rem] font-medium text-neutral-400 hover:text-neutral-700"
              type="button"
              @click="sessionStore.emailChallenge = null"
          >
            Change email
          </button>
        </div>
      </form>
    </AuthCard>
  </AuthShell>
</template>
