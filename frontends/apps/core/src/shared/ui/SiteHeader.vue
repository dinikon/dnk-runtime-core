<script setup lang="ts">
import { Button } from "@dnk/ui/components/button";
defineProps<{ authenticated: boolean | null; showAdminLink: boolean }>();
</script>

<template>
  <header class="site-header" :class="{ 'site-header--admin': authenticated && showAdminLink }">
    <NuxtLink to="/" class="brand" aria-label="dNiko Alpha — главная">dNiko <span>Alpha</span></NuxtLink>
    <nav class="header-nav" aria-label="Основная навигация">
      <template v-if="authenticated">
        <a href="/accounts/" class="nav-link">Аккаунт и безопасность</a>
        <Button as-child variant="outline"><NuxtLink to="/app/">Мой аккаунт</NuxtLink></Button>
        <Button v-if="showAdminLink" as="a" href="/admin/" variant="outline">Django admin</Button>
      </template>
      <Button v-else as="a" href="/accounts/login/?next=/app/" variant="outline">Войти</Button>
    </nav>
  </header>
</template>
