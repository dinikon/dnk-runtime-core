<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Loader2 } from "@lucide/vue";
import { useRoute, useRouter } from "vue-router";

import { getApiErrorMessage } from "@/app/providers/http";
import { useTenantStore } from "@/app/stores/tenant";
import { useUserStore } from "@/app/stores/user";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { AuthLayout } from "@/layouts";
import AuthPageTitle from "@/modules/auth/components/AuthPageTitle.vue";
import ConfirmOtpForm from "@/modules/auth/features/confirm-otp/ConfirmOtpForm.vue";
import RequestOtpForm from "@/modules/auth/features/request-otp/RequestOtpForm.vue";
import { authApi } from "@/modules/auth/api/auth.api";
import { useConfirmOtpMutation } from "@/modules/auth/mutations/use-confirm-otp";
import { useRequestOtpMutation } from "@/modules/auth/mutations/use-request-otp";
import type {
  AuthLoginStep,
  EmailChallenge,
} from "@/modules/auth/model/auth.types";

const route = useRoute();
const router = useRouter();
const tenantStore = useTenantStore();
const userStore = useUserStore();
const requestOtpMutation = useRequestOtpMutation();
const confirmOtpMutation = useConfirmOtpMutation();
const emailChallenge = ref<EmailChallenge | null>(null);
const authError = ref<string | null>(null);

const loginStep = computed<AuthLoginStep>(() => {
  if (tenantStore.isResolvingTenant || !tenantStore.tenant) {
    return "checking";
  }

  if (!tenantStore.isTenantAvailable) {
    return "workspace-not-found";
  }

  return emailChallenge.value ? "confirm-otp" : "request-otp";
});

onMounted(() => {
  void tenantStore.resolveTenant();
});

async function requestOtp(email: string) {
  authError.value = null;

  try {
    const result = await requestOtpMutation.mutateAsync({ email });
    emailChallenge.value = {
      email,
      token: result.token,
      expiresIn: result.expires_in,
      devCode: result.code ?? null,
    };
  } catch (error) {
    authError.value = getApiErrorMessage(
      error,
      "We could not send a verification email.",
    );
  }
}

async function confirmOtp(code: string) {
  if (!emailChallenge.value) {
    return;
  }

  authError.value = null;

  try {
    await confirmOtpMutation.mutateAsync({
      email: emailChallenge.value.email,
      token: emailChallenge.value.token,
      code,
    });
    userStore.setUser(await authApi.getCurrentUser());
    await redirectAfterLogin();
  } catch (error) {
    authError.value = getApiErrorMessage(
      error,
      "The verification code is invalid, expired, or the session could not be loaded.",
    );
  }
}

async function resendOtp() {
  if (!emailChallenge.value) {
    return;
  }

  await requestOtp(emailChallenge.value.email);
}

function changeEmail() {
  emailChallenge.value = null;
  authError.value = null;
}

async function redirectAfterLogin() {
  const redirect = route.query.redirect;
  emailChallenge.value = null;
  authError.value = null;

  await router.replace(
    typeof redirect === "string" ? redirect : { name: "dashboard" },
  );
}
</script>

<template>
  <AuthLayout>
    <Card v-if="loginStep === 'checking'" class="w-full max-w-sm">
      <CardHeader class="items-center">
        <AuthPageTitle
          title="Loading workspace"
          description="Checking the current workspace address."
        >
          <template #icon>
            <Loader2
              class="mx-auto size-5 animate-spin text-muted-foreground"
              aria-hidden="true"
            />
          </template>
        </AuthPageTitle>
      </CardHeader>
    </Card>

    <Card
      v-else-if="loginStep === 'workspace-not-found'"
      class="w-full max-w-sm"
    >
      <CardHeader>
        <AuthPageTitle
          title="Welcome to dNiko"
          description="This workspace was not found or is not available for login."
        />
      </CardHeader>
      <CardContent class="grid gap-4">
        <Alert>
          <AlertDescription>
            Check the workspace address or contact your workspace administrator.
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>

    <RequestOtpForm
      v-else-if="loginStep === 'request-otp'"
      :auth-error="authError"
      :is-submitting="requestOtpMutation.isPending.value"
      @request="requestOtp"
    />
    <ConfirmOtpForm
      v-else-if="emailChallenge"
      :auth-error="authError"
      :email-challenge="emailChallenge"
      :is-confirming="confirmOtpMutation.isPending.value"
      :is-resending="requestOtpMutation.isPending.value"
      @change-email="changeEmail"
      @confirm="confirmOtp"
      @resend="resendOtp"
    />
  </AuthLayout>
</template>
