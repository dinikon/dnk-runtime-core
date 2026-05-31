<script setup lang="ts">
import { computed, ref } from "vue";
import { Mail } from "lucide-vue-next";
import { REGEXP_ONLY_DIGITS } from "vue-input-otp";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from "@/components/ui/card";
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
} from "@/components/ui/input-otp";
import { Label } from "@/components/ui/label";
import AuthErrorAlert from "@/modules/auth/components/AuthErrorAlert.vue";
import AuthPageTitle from "@/modules/auth/components/AuthPageTitle.vue";
import type { EmailChallenge } from "@/modules/auth/model/auth.types";

const props = defineProps<{
  authError: string | null;
  emailChallenge: EmailChallenge;
  isConfirming: boolean;
  isResending: boolean;
}>();

const emit = defineEmits<{
  changeEmail: [];
  confirm: [code: string];
  resend: [];
}>();

const OTP_CODE_LENGTH = 6;

const code = ref("");

const canConfirmOtp = computed(
  () => code.value.length === OTP_CODE_LENGTH && !props.isConfirming,
);

function confirmOtp() {
  if (!canConfirmOtp.value) {
    return;
  }

  emit("confirm", code.value);
}

function resendOtp() {
  if (props.isResending) {
    return;
  }

  emit("resend");
  code.value = "";
}

function changeEmail() {
  emit("changeEmail");
  code.value = "";
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
            emailChallenge.email
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
          <InputOTP
            id="auth-code"
            v-model="code"
            :maxlength="OTP_CODE_LENGTH"
            :pattern="REGEXP_ONLY_DIGITS"
            class="justify-center"
            inputmode="numeric"
            autocomplete="one-time-code"
          >
            <InputOTPGroup class="gap-2">
              <InputOTPSlot
                v-for="index in OTP_CODE_LENGTH"
                :key="index"
                :index="index - 1"
                class="rounded-md border-l"
              />
            </InputOTPGroup>
          </InputOTP>
        </div>

        <Alert v-if="emailChallenge.devCode">
          <AlertDescription>
            Development code: {{ emailChallenge.devCode }}
          </AlertDescription>
        </Alert>

        <Button class="w-full" type="submit" :disabled="!canConfirmOtp">
          {{ isConfirming ? "Checking..." : "Continue" }}
        </Button>

        <AuthErrorAlert :message="authError" />

        <div class="flex justify-center gap-3">
          <Button
            variant="link"
            size="sm"
            type="button"
            class="h-auto px-0 text-muted-foreground"
            :disabled="isResending"
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
