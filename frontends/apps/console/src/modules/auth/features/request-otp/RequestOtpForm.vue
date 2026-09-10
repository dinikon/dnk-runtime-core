<script setup lang="ts">
import { computed, ref } from "vue";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import AuthErrorAlert from "@/modules/auth/components/AuthErrorAlert.vue";
import AuthPageTitle from "@/modules/auth/components/AuthPageTitle.vue";

const props = defineProps<{
  authError: string | null;
  isSubmitting: boolean;
}>();

const emit = defineEmits<{
  request: [email: string];
}>();

const email = ref("");

const canRequestOtp = computed(
  () => email.value.trim().length > 3 && !props.isSubmitting,
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
      <form class="grid gap-4" @submit.prevent="requestOtp">
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
          {{ isSubmitting ? "Sending..." : "Continue" }}
        </Button>

        <AuthErrorAlert :message="authError" />

        <p
          class="px-1 text-center text-xs leading-relaxed text-muted-foreground"
        >
          By using dNiko, you agree to the Terms of Service and Data Processing
          Agreement.
        </p>
      </form>
    </CardContent>
  </Card>
</template>
