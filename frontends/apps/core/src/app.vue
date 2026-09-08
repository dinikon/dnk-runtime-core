<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";
import { useRoute } from "#imports";
import { loginUrl, useCoreSession } from "./modules/session/model/session";
import SiteHeader from "./shared/ui/SiteHeader.vue";
import SiteFooter from "./shared/ui/SiteFooter.vue";

const route = useRoute();
const { session, refreshSession } = useCoreSession();

async function checkSession() {
  await refreshSession();
  if (route.meta.requiresAuth && !session.value.error && session.value.authenticated === false) {
    window.location.assign(loginUrl(route.fullPath));
  }
}

function onVisibilityChange() {
  if (document.visibilityState === "visible") void checkSession();
}

onMounted(() => {
  void checkSession();
  document.addEventListener("visibilitychange", onVisibilityChange);
});
onUnmounted(() => document.removeEventListener("visibilitychange", onVisibilityChange));
</script>

<template>
  <div class="site-shell">
    <a class="skip-link" href="#main-content">К содержимому</a>
    <SiteHeader :authenticated="session.authenticated" />
    <main id="main-content" class="site-main"><NuxtPage /></main>
    <SiteFooter />
  </div>
</template>
