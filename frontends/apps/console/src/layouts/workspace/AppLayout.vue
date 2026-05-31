<script setup lang="ts">
import { LogOut, Menu } from "lucide-vue-next";
import { useRouter } from "vue-router";

import { useSessionStore } from "@/app/stores/session";
import { Button } from "@/components/ui/button";

const router = useRouter();
const sessionStore = useSessionStore();

async function logout() {
  await sessionStore.logout();
  await router.push({ name: "login" });
}
</script>

<template>
  <div class="grid min-h-svh bg-background">
    <header class="flex h-14 items-center gap-3 border-b px-4">
      <Button
        variant="ghost"
        size="icon"
        type="button"
        aria-label="Open navigation"
        disabled
      >
        <Menu class="size-4" aria-hidden="true" />
      </Button>

      <div class="min-w-0 flex-1">
        <slot name="header" />
      </div>

      <div class="hidden min-w-0 text-right text-sm sm:block">
        <p class="truncate font-medium">
          {{ sessionStore.user?.first_name }} {{ sessionStore.user?.last_name }}
        </p>
        <p class="truncate text-xs text-muted-foreground">
          {{ sessionStore.primaryEmail }}
        </p>
      </div>

      <Button
        variant="outline"
        size="sm"
        type="button"
        :disabled="sessionStore.isLoggingOut"
        @click="logout"
      >
        <LogOut class="size-4" aria-hidden="true" />
        Logout
      </Button>
    </header>

    <section class="min-h-0 p-4">
      <slot />
    </section>
  </div>
</template>
