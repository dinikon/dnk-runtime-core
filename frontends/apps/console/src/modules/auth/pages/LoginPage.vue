<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
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
import { useConfirmOtpMutation } from "@/modules/auth/mutations/use-confirm-otp";
import { useRequestOtpMutation } from "@/modules/auth/mutations/use-request-otp";
import { useCloudStatusQuery } from "../model/use-cloud-status-query";
import { useStartCloudAuth } from "../model/use-start-cloud-auth";
import {
  requestsCloudLogin,
  withoutAuthProvider,
} from "../model/cloud-navigation";
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
const cloudStatus = useCloudStatusQuery(
  () => tenantStore.tenant?.tenant_id ?? null,
);
const startCloudAuth = useStartCloudAuth();
const initializing = ref(true);
const cloudLoading = ref(true);
const cloudEnabled = computed(() => cloudStatus.data.value?.enabled !== false);
const cloudBusy = ref(false);
const automaticCloudLogin =
  requestsCloudLogin(route.query.auth_provider) && !route.query.cloud_error;
let active = true;
onBeforeUnmount(() => {
  active = false;
});
const cloudError = ref(
  route.query.cloud_error
    ? "Cloud sign-in could not be completed. Please try again or use an email code."
    : "",
);

const loginStep = computed<AuthLoginStep>(() => {
  if (
    initializing.value ||
    tenantStore.isResolvingTenant ||
    !tenantStore.tenant
  ) {
    return "checking";
  }

  if (!tenantStore.isTenantAvailable) {
    return "workspace-not-found";
  }

  return emailChallenge.value ? "confirm-otp" : "request-otp";
});

onMounted(async () => {
  // Consume the navigation hint before starting any request or leaving this page.
  if (route.query.auth_provider !== undefined) {
    const query = { ...route.query };
    delete query.auth_provider;
    await router.replace({ path: route.path, query, hash: route.hash });
  }
  await tenantStore.resolveTenant();
  if (!active) return;
  if (tenantStore.isTenantAvailable && userStore.sessionStatus !== "error") {
    try {
      await userStore.ensureCurrentUser();
      if (active) await redirectAfterLogin();
      return;
    } catch {
      // No local session: both login methods remain available.
    }
  }
  initializing.value = false;
  if (!tenantStore.isTenantAvailable || !active) return;
  const status = await cloudStatus.refetch();
  if (!active) return;
  cloudLoading.value = false;
  if (status.error) {
    cloudError.value =
      "Could not check dNiko sign-in. Try again or use an email code.";
  } else if (automaticCloudLogin && status.data?.enabled) {
    await cloudLogin(true);
  }
});

async function cloudLogin(silent = false): Promise<void> {
  if (cloudBusy.value || requestOtpMutation.isPending.value) return;
  if (silent && emailChallenge.value) return;
  cloudBusy.value = true;
  cloudError.value = "";
  try {
    const url = await startCloudAuth.mutateAsync({ purpose: "login", silent });
    if (active) window.location.assign(url);
  } catch (error) {
    cloudError.value = getApiErrorMessage(
      error,
      "Cloud sign-in is unavailable. You can still use an email code.",
    );
    cloudBusy.value = false;
  }
}

async function requestOtp(email: string) {
  if (cloudBusy.value || requestOtpMutation.isPending.value) return;
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
    await userStore.ensureCurrentUser();
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
    typeof redirect === "string" &&
      redirect.startsWith("/") &&
      !redirect.startsWith("//")
      ? withoutAuthProvider(redirect)
      : { name: "dashboard" },
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
      :cloud-enabled="cloudEnabled"
      :cloud-loading="cloudLoading"
      :cloud-busy="cloudBusy"
      :cloud-error="cloudError"
      @request="requestOtp"
      @cloud-login="cloudLogin()"
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
