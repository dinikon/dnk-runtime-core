<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";
import { useRoute } from "#imports";
import { loginUrl, useCoreSession } from "./modules/session/model/session";
import { useCoreCapabilities } from "./modules/capabilities/model/capabilities";
import SiteHeader from "./shared/ui/SiteHeader.vue";
import SiteFooter from "./shared/ui/SiteFooter.vue";

const route = useRoute();
const { session, refreshSession } = useCoreSession();
const { refreshCapabilities } = useCoreCapabilities();

async function checkSession() {
  await refreshSession();
  if (route.meta.requiresAuth && !session.value.error && session.value.authenticated === false) {
    window.location.assign(loginUrl(route.fullPath));
  }
}

function onVisibilityChange() {
  if (document.visibilityState === "visible") {
    void checkSession();
    void refreshCapabilities();
  }
}

onMounted(() => {
  void checkSession();
  void refreshCapabilities();
  document.addEventListener("visibilitychange", onVisibilityChange);
});
onUnmounted(() => document.removeEventListener("visibilitychange", onVisibilityChange));
</script>

<template>
  <div class="site-shell">
    <a class="skip-link" href="#main-content">К содержимому</a>
    <SiteHeader :authenticated="session.authenticated" :show-admin-link="session.showAdminLink" />
    <main id="main-content" class="site-main"><NuxtPage /></main>
    <SiteFooter />
  </div>
</template>
