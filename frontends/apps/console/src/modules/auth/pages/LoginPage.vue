<script setup lang="ts">
import { computed, onMounted } from "vue";
import { Loader2 } from "lucide-vue-next";
import { useRouter } from "vue-router";

import { useTenantStore } from "@/app/stores/tenant";
import { useUserStore } from "@/app/stores/user";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { AuthLayout } from "@/layouts";
import AuthPageTitle from "@/modules/auth/components/AuthPageTitle.vue";
import ConfirmOtpForm from "@/modules/auth/features/confirm-otp/ConfirmOtpForm.vue";
import RequestOtpForm from "@/modules/auth/features/request-otp/RequestOtpForm.vue";
import type { AuthLoginStep } from "@/modules/auth/model/auth.types";

const router = useRouter();
const tenantStore = useTenantStore();
const userStore = useUserStore();

const loginStep = computed<AuthLoginStep>(() => {
  if (tenantStore.isResolvingTenant || !tenantStore.tenant) {
    return "checking";
  }

  if (!tenantStore.isTenantAvailable) {
    return "workspace-not-found";
  }

  return userStore.emailChallenge ? "confirm-otp" : "request-otp";
});

onMounted(() => {
  void tenantStore.resolveTenant();
});

async function redirectAfterLogin() {
  await router.replace({ name: "dashboard" });
  userStore.clearEmailChallenge();
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

    <RequestOtpForm v-else-if="loginStep === 'request-otp'" />
    <ConfirmOtpForm v-else @confirmed="redirectAfterLogin" />
  </AuthLayout>
</template>
