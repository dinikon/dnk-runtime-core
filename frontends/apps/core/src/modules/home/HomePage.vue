<script setup lang="ts">
import { useCoreSession } from "../session/model/session";
const { session, refreshSession } = useCoreSession();
</script>

<template>
  <section class="hero" aria-labelledby="hero-title">
    <h1 id="hero-title">dNiko Alpha — единый аккаунт для вашей работы</h1>
    <p>Управляйте профилем, способами входа и безопасностью в одном месте</p>
    <div class="hero-actions">
      <NuxtLink v-if="session.authenticated" to="/app/" class="button">Открыть приложение</NuxtLink>
      <template v-else>
        <a href="/accounts/signup/?next=/app/" class="button">Создать аккаунт</a>
        <a href="/accounts/login/?next=/app/" class="button button-outline">Войти</a>
      </template>
    </div>
    <div v-if="session.error" class="hero-session-error" role="status">
      <p>Не удалось проверить аккаунт. Попробуйте ещё раз.</p>
      <button type="button" :disabled="session.loading" @click="refreshSession">Повторить</button>
    </div>
  </section>
</template>
