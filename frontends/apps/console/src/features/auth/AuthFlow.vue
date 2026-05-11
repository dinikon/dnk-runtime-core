<script setup lang="ts">
import {computed, onMounted, ref} from "vue";
import {useRouter} from "vue-router";
import {Loader2, Mail} from "lucide-vue-next";

import {useSessionStore} from "@/app/stores/session";
import {Alert, AlertDescription} from "@/components/ui/alert";
import {Button} from "@/components/ui/button";
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from "@/components/ui/card";
import {Input} from "@/components/ui/input";
import {Label} from "@/components/ui/label";
import {AuthProviderButton, OtpCodeInput} from "@/features/auth/components";

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
  <Card v-if="loginStep === 'checking'" class="w-full max-w-sm text-center">
    <CardHeader class="items-center">
      <Loader2 class="size-5 animate-spin text-muted-foreground" aria-hidden="true"/>
      <CardTitle class="text-base">Loading workspace</CardTitle>
      <CardDescription>Checking the current workspace address.</CardDescription>
    </CardHeader>
  </Card>

  <Card v-else-if="loginStep === 'workspace-not-found'" class="w-full max-w-sm">
    <CardHeader class="text-center">
      <CardTitle class="text-base">Вітаємо в dNiko</CardTitle>
      <CardDescription>Робочий простір за цією адресою не знайдено або він недоступний.</CardDescription>
    </CardHeader>
    <CardContent class="grid gap-4">
      <Alert>
        <AlertDescription>
          By using dNiko, you agree to the Terms of Service and Data Processing Agreement.
        </AlertDescription>
      </Alert>
    </CardContent>
  </Card>

  <Card v-else-if="loginStep === 'email'" class="w-full max-w-sm">
    <CardHeader class="text-center">
      <CardTitle class="text-base">Welcome to dNiko</CardTitle>
      <CardDescription>Enter your email to continue.</CardDescription>
    </CardHeader>
    <CardContent>
      <form class="grid gap-4" @submit.prevent="requestOtp">
        <div class="grid gap-2">
          <AuthProviderButton provider="google" disabled>
            Continue with Google
          </AuthProviderButton>
          <AuthProviderButton provider="microsoft" disabled>
            Continue with Microsoft
          </AuthProviderButton>
        </div>

        <div class="grid gap-2">
          <Label for="auth-email">Email</Label>
          <Input
              id="auth-email"
              v-model="email"
              class="text-center"
              type="email"
              autocomplete="email"
              placeholder="tim@apple.dev"
              required
          />
        </div>

        <Button class="w-full" type="submit" :disabled="!canRequestOtp">
          {{ sessionStore.isRequestingOtp ? "Sending..." : "Continue" }}
        </Button>

        <Alert v-if="sessionStore.authError" variant="destructive">
          <AlertDescription>{{ sessionStore.authError }}</AlertDescription>
        </Alert>

        <p class="px-1 text-center text-xs leading-relaxed text-muted-foreground">
          By using dNiko, you agree to the Terms of Service and Data Processing Agreement.
        </p>
      </form>
    </CardContent>
  </Card>

  <Card v-else class="w-full max-w-sm">
    <CardHeader class="items-center text-center">
      <div class="grid size-9 place-items-center rounded-full border">
        <Mail class="size-4" aria-hidden="true"/>
      </div>
      <CardTitle class="text-base">Check your Emails</CardTitle>
      <CardDescription>
        A verification email has been sent to:
        <strong class="block text-foreground">{{ sessionStore.emailChallenge?.email }}</strong>
      </CardDescription>
    </CardHeader>
    <CardContent>
      <form class="grid gap-4" @submit.prevent="confirmOtp">
        <div class="grid gap-2">
          <AuthProviderButton provider="google" variant="outline" @click="openMail('gmail')">
            Open Gmail
          </AuthProviderButton>
          <AuthProviderButton provider="microsoft" variant="outline" @click="openMail('outlook')">
            Open Outlook
          </AuthProviderButton>
        </div>

        <div class="grid gap-2">
          <Label>Verification code</Label>
          <OtpCodeInput v-model="code"/>
        </div>

        <Alert v-if="sessionStore.emailChallenge?.devCode">
          <AlertDescription>
            Development code: {{ sessionStore.emailChallenge.devCode }}
          </AlertDescription>
        </Alert>

        <Button class="w-full" type="submit" :disabled="!canConfirmOtp">
          {{ sessionStore.isConfirmingOtp ? "Checking..." : "Continue" }}
        </Button>

        <Alert v-if="sessionStore.authError" variant="destructive">
          <AlertDescription>{{ sessionStore.authError }}</AlertDescription>
        </Alert>

        <div class="flex justify-center gap-3">
          <Button variant="link" size="sm" type="button" class="h-auto px-0 text-muted-foreground" @click="requestOtp">
            Resend email
          </Button>
          <Button
              variant="link"
              size="sm"
              type="button"
              class="h-auto px-0 text-muted-foreground"
              @click="sessionStore.emailChallenge = null"
          >
            Change email
          </Button>
        </div>
      </form>
    </CardContent>
  </Card>
</template>
