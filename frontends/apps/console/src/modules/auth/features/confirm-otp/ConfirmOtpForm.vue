<script setup lang="ts">
import { computed, ref } from "vue";
import { Mail } from "lucide-vue-next";

import { useSessionStore } from "@/app/stores/session";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import AuthErrorAlert from "@/modules/auth/components/AuthErrorAlert.vue";
import AuthPageTitle from "@/modules/auth/components/AuthPageTitle.vue";
import { useConfirmOtpMutation } from "@/modules/auth/mutations/use-confirm-otp";
import { useRequestOtpMutation } from "@/modules/auth/mutations/use-request-otp";

const emit = defineEmits<{
  confirmed: [];
}>();

const code = ref("");
const sessionStore = useSessionStore();
const confirmOtpMutation = useConfirmOtpMutation();
const requestOtpMutation = useRequestOtpMutation();

const canConfirmOtp = computed(
  () => code.value.length === 6 && !confirmOtpMutation.isPending.value,
);

async function confirmOtp() {
  if (!canConfirmOtp.value) {
    return;
  }

  await confirmOtpMutation.mutateAsync({ code: code.value });
  emit("confirmed");
}

async function resendOtp() {
  const email = sessionStore.emailChallenge?.email;
  if (!email || requestOtpMutation.isPending.value) {
    return;
  }

  await requestOtpMutation.mutateAsync({ email });
  code.value = "";
}

function changeEmail() {
  sessionStore.clearEmailChallenge();
  code.value = "";
}

function updateCode(value: string | number) {
  code.value = String(value).replace(/\D/g, "").slice(0, 6);
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
  <Card class="w-full max-w-sm">
    <CardHeader class="items-center text-center">
      <AuthPageTitle title="Check your email">
        <template #icon>
          <div
            class="mx-auto grid size-9 place-items-center rounded-full border"
          >
            <Mail class="size-4" aria-hidden="true" />
          </div>
        </template>
        <CardDescription>
          A verification email has been sent to:
          <strong class="block text-foreground">{{
            sessionStore.emailChallenge?.email
          }}</strong>
        </CardDescription>
      </AuthPageTitle>
    </CardHeader>
    <CardContent>
      <form class="grid gap-4" @submit.prevent="confirmOtp">
        <div class="grid gap-2">
          <Button
            type="button"
            variant="outline"
            class="w-full"
            @click="openMail('gmail')"
          >
            <span
              class="grid size-4 place-items-center rounded-[3px] bg-[#4285f4] text-[0.6rem] font-extrabold text-white"
              aria-hidden="true"
            >
              G
            </span>
            Open Gmail
          </Button>
          <Button
            type="button"
            variant="outline"
            class="w-full"
            @click="openMail('outlook')"
          >
            <span
              class="grid size-4 place-items-center rounded-[3px] bg-[#f25022] text-[0.6rem] font-extrabold text-white"
              aria-hidden="true"
            >
              M
            </span>
            Open Outlook
          </Button>
        </div>

        <div class="grid gap-2">
          <Label for="auth-code">Verification code</Label>
          <Input
            id="auth-code"
            :model-value="code"
            class="text-center tracking-[0.35em]"
            inputmode="numeric"
            autocomplete="one-time-code"
            maxlength="6"
            @update:model-value="updateCode"
          />
        </div>

        <Alert v-if="sessionStore.emailChallenge?.devCode">
          <AlertDescription>
            Development code: {{ sessionStore.emailChallenge.devCode }}
          </AlertDescription>
        </Alert>

        <Button class="w-full" type="submit" :disabled="!canConfirmOtp">
          {{ confirmOtpMutation.isPending.value ? "Checking..." : "Continue" }}
        </Button>

        <AuthErrorAlert :message="sessionStore.authError" />

        <div class="flex justify-center gap-3">
          <Button
            variant="link"
            size="sm"
            type="button"
            class="h-auto px-0 text-muted-foreground"
            :disabled="requestOtpMutation.isPending.value"
            @click="resendOtp"
          >
            Resend email
          </Button>
          <Button
            variant="link"
            size="sm"
            type="button"
            class="h-auto px-0 text-muted-foreground"
            @click="changeEmail"
          >
            Change email
          </Button>
        </div>
      </form>
    </CardContent>
  </Card>
</template>
