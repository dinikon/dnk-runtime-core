<script setup lang="ts">
defineProps<{ authenticated: boolean | null }>();
</script>

<template>
  <header class="site-header">
    <NuxtLink to="/" class="brand" aria-label="dNiko Alpha — главная">dNiko <span>Alpha</span></NuxtLink>
    <nav class="header-nav" aria-label="Основная навигация">
      <template v-if="authenticated">
        <a href="/accounts/" class="nav-link">Аккаунт и безопасность</a>
        <NuxtLink to="/app/" class="button button-small button-outline">Мой аккаунт</NuxtLink>
      </template>
      <a v-else href="/accounts/login/?next=/app/" class="button button-small button-outline">Войти</a>
    </nav>
  </header>
</template>
