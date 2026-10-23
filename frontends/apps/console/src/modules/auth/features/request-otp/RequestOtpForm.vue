<script setup lang="ts">
import { computed, ref } from "vue";
import { Cloud, Loader2 } from "@lucide/vue";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldSeparator,
  FieldDescription,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import AuthErrorAlert from "@/modules/auth/components/AuthErrorAlert.vue";
import AuthPageTitle from "@/modules/auth/components/AuthPageTitle.vue";

const props = defineProps<{
  authError: string | null;
  isSubmitting: boolean;
  cloudEnabled: boolean;
  cloudLoading: boolean;
  cloudBusy: boolean;
  cloudError: string | null;
}>();

const emit = defineEmits<{
  request: [email: string];
  cloudLogin: [];
}>();

const email = ref("");

const canRequestOtp = computed(
  () =>
    email.value.trim().length > 3 && !props.isSubmitting && !props.cloudBusy,
);

function requestOtp() {
  if (!canRequestOtp.value) {
    return;
  }

  emit("request", email.value.trim());
}
</script>

<template>
  <Card class="w-full max-w-sm">
    <CardHeader>
      <AuthPageTitle
        title="Welcome to dNiko"
        description="Enter your email to continue."
      />
    </CardHeader>
    <CardContent>
      <form @submit.prevent="requestOtp">
        <FieldGroup class="gap-5">
          <Field :data-disabled="isSubmitting || cloudBusy">
            <FieldLabel for="auth-email">Email</FieldLabel>
            <Input
              id="auth-email"
              v-model="email"
              type="email"
              autocomplete="email"
              placeholder="name@example.com"
              :disabled="isSubmitting || cloudBusy"
              required
            />
          </Field>

          <Button class="w-full" type="submit" :disabled="!canRequestOtp">
            {{ isSubmitting ? "Sending..." : "Continue" }}
          </Button>

          <AuthErrorAlert :message="authError" />
          <FieldSeparator>Or</FieldSeparator>
          <Field>
            <Button
              type="button"
              variant="outline"
              class="w-full"
              :disabled="
                !cloudEnabled || cloudLoading || cloudBusy || isSubmitting
              "
              :aria-busy="cloudBusy || cloudLoading"
              @click="emit('cloudLogin')"
            >
              <Loader2
                v-if="cloudBusy || cloudLoading"
                class="animate-spin"
                data-icon="inline-start"
                aria-hidden="true"
              />
              <Cloud v-else data-icon="inline-start" aria-hidden="true" />
              {{ cloudBusy ? "Connecting…" : "Continue with dNiko" }}
            </Button>
            <FieldDescription v-if="!cloudEnabled" class="text-center">
              dNiko sign-in is not configured for this workspace.
            </FieldDescription>
            <AuthErrorAlert :message="cloudError" />
          </Field>
        </FieldGroup>
      </form>
    </CardContent>
    <CardFooter>
      <p class="text-center text-xs leading-relaxed text-muted-foreground">
        By using dNiko, you agree to the Terms of Service and Data Processing
        Agreement.
      </p>
    </CardFooter>
  </Card>
</template>
