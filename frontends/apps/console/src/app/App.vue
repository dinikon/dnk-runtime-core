<script setup lang="ts">
import {computed} from "vue";
import {useRoute} from "vue-router";

const route = useRoute();
const isAuthLayout = computed(() => route.meta.layout === "auth");
</script>

<template>
  <div class="console-shell" :class="{'console-shell--auth': isAuthLayout}">
    <header v-if="!isAuthLayout" class="console-header">
      <RouterLink class="brand" to="/">DNK Console</RouterLink>
      <nav class="main-nav" aria-label="Primary">
        <RouterLink to="/">Home</RouterLink>
        <RouterLink to="/login">Login</RouterLink>
      </nav>
    </header>

    <main :class="isAuthLayout ? 'console-main-auth' : 'console-main'">
      <RouterView/>
    </main>
  </div>
</template>
