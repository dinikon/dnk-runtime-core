<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { getApiErrorMessage } from "@/app/providers/http";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { accessApi } from "../api";

const status = ref<{ enabled: boolean; linked: boolean } | null>(null);
const busy = ref(false);
const error = ref(
  useRoute().query.cloud_error
    ? "The cloud account could not be linked. Your local account has not changed."
    : "",
);
onMounted(async () => {
  try {
    status.value = await accessApi.cloudStatus();
  } catch (cause) {
    error.value = getApiErrorMessage(
      cause,
      "Could not load your cloud account.",
    );
  }
});
async function link() {
  busy.value = true;
  try {
    window.location.assign(
      (await accessApi.cloudStart("link")).authorization_url,
    );
  } catch (cause) {
    error.value = getApiErrorMessage(
      cause,
      "Cloud sign-in is unavailable. Please try again.",
    );
    busy.value = false;
  }
}
async function unlink() {
  busy.value = true;
  try {
    await accessApi.cloudUnlink();
    window.location.assign("/login");
  } catch (cause) {
    error.value = getApiErrorMessage(cause, "Could not unlink this account.");
    busy.value = false;
  }
}
</script>
<template>
  <div class="flex flex-col gap-6 overflow-y-auto">
    <h1 class="text-2xl font-semibold">Account</h1>
    <Alert v-if="error" variant="destructive" role="alert"
      ><AlertDescription>{{ error }}</AlertDescription></Alert
    >
    <Card class="max-w-2xl"
      ><CardHeader
        ><CardTitle>Cloud account</CardTitle
        ><CardDescription
          >Link your cloud account to sign in to this workspace. Email
          verification remains available.</CardDescription
        ></CardHeader
      ><CardContent class="flex flex-col gap-4">
        <p v-if="!status" role="status">Loading account…</p>
        <template v-else-if="status.enabled"
          ><p>
            {{
              status.linked
                ? "Your cloud account is linked."
                : "No cloud account is linked."
            }}
          </p>
          <Button
            v-if="!status.linked"
            class="self-start"
            :disabled="busy"
            @click="link"
            >Link cloud account</Button
          ><template v-else
            ><p class="text-sm text-muted-foreground">
              Unlinking signs you out of all local sessions. You can sign in
              again using an email code.
            </p>
            <Button
              variant="outline"
              class="self-start"
              :disabled="busy"
              @click="unlink"
              >Unlink cloud account</Button
            ></template
          ></template
        >
        <p v-else class="text-muted-foreground">
          Cloud sign-in is not configured for this workspace.
        </p>
      </CardContent></Card
    >
  </div>
</template>
