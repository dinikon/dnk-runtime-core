<script setup lang="ts">
import { LogOut } from "@lucide/vue";
import { useRouter } from "vue-router";

import { Button } from "@/components/ui/button";
import { useLogoutMutation } from "@/modules/auth/mutations/use-logout";

const router = useRouter();
const logoutMutation = useLogoutMutation();

async function logout() {
  await logoutMutation.mutateAsync();
  await router.push({ name: "login" });
}
</script>

<template>
  <Button
    variant="outline"
    size="sm"
    type="button"
    :disabled="logoutMutation.isPending.value"
    @click="logout"
  >
    <LogOut class="size-4" aria-hidden="true" />
    Logout
  </Button>
</template>
