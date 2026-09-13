<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getApiErrorMessage } from "@/app/providers/http";
import { useUserStore } from "@/app/stores/user";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { AuthLayout } from "@/layouts";
import { authApi } from "@/modules/auth/api/auth.api";
import { accessApi } from "../api";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const invitationToken =
  typeof route.query.token === "string" ? route.query.token : "";
const otpToken = ref("");
const code = ref("");
const firstName = ref("");
const lastName = ref("");
const busy = ref(false);
const error = ref(
  invitationToken
    ? ""
    : "This invitation link is incomplete. Ask your administrator for a new link.",
);
async function requestCode() {
  busy.value = true;
  error.value = "";
  try {
    otpToken.value = (
      await accessApi.requestInvitationOtp(invitationToken)
    ).token;
  } catch (cause) {
    error.value = getApiErrorMessage(
      cause,
      "This invitation is expired or unavailable. Ask your administrator for a new link.",
    );
  } finally {
    busy.value = false;
  }
}
async function accept() {
  busy.value = true;
  error.value = "";
  try {
    await accessApi.acceptInvitation({
      invitation_token: invitationToken,
      token: otpToken.value,
      code: code.value,
      first_name: firstName.value,
      last_name: lastName.value,
    });
    userStore.setUser(await authApi.getCurrentUser());
    await router.replace("/settings/account");
  } catch (cause) {
    error.value = getApiErrorMessage(
      cause,
      "Could not accept the invitation. Check your code or request a new one.",
    );
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <AuthLayout
    ><Card class="w-full max-w-md"
      ><CardHeader
        ><CardTitle>Join this workspace</CardTitle
        ><CardDescription
          >Verify the email your administrator invited. You can link a cloud
          account after joining.</CardDescription
        ></CardHeader
      ><CardContent class="flex flex-col gap-4">
        <Alert v-if="error" variant="destructive" role="alert"
          ><AlertDescription>{{ error }}</AlertDescription></Alert
        >
        <Button
          v-if="!otpToken"
          :disabled="busy || !invitationToken"
          @click="requestCode"
          >{{ busy ? "Sending…" : "Send verification code" }}</Button
        >
        <form v-else @submit.prevent="accept">
          <FieldGroup>
            <Field
              ><FieldLabel for="invitation-code">Verification code</FieldLabel
              ><Input
                id="invitation-code"
                v-model="code"
                inputmode="numeric"
                autocomplete="one-time-code"
                maxlength="6"
                pattern="[0-9]{6}"
                required
                :disabled="busy"
            /></Field>
            <Field
              ><FieldLabel for="first-name">First name</FieldLabel
              ><Input
                id="first-name"
                v-model="firstName"
                autocomplete="given-name"
                required
                :disabled="busy"
            /></Field>
            <Field
              ><FieldLabel for="last-name">Last name</FieldLabel
              ><Input
                id="last-name"
                v-model="lastName"
                autocomplete="family-name"
                required
                :disabled="busy"
            /></Field>
            <Button type="submit" :disabled="busy">{{
              busy ? "Joining…" : "Join workspace"
            }}</Button>
            <Button
              variant="ghost"
              type="button"
              :disabled="busy"
              @click="requestCode"
              >Send a new code</Button
            >
          </FieldGroup>
        </form>
      </CardContent></Card
    ></AuthLayout
  >
</template>
