<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "#imports";
import { loginUrl, useCoreSession } from "../session/model/session";
import ProfileOverview from "./ui/ProfileOverview.vue";

const route = useRoute();
const { session, refreshSession } = useCoreSession();
const displayName = computed(() =>
  [session.value.user?.first_name, session.value.user?.last_name].filter(Boolean).join(" ") || session.value.user?.username || "Ваш аккаунт",
);

async function retry() {
  await refreshSession();
  if (!session.value.error && session.value.authenticated === false) window.location.assign(loginUrl(route.fullPath));
}
</script>

<template>
  <section class="workspace" aria-labelledby="workspace-title">
    <header class="page-heading">
      <p class="muted">Мой аккаунт</p>
      <h1 id="workspace-title">{{ displayName }}</h1>
      <p class="muted">Профиль и настройки вашего аккаунта dNiko Alpha.</p>
    </header>
    <div v-if="session.error" class="alert" role="alert">
      <h2>Не удалось загрузить аккаунт</h2>
      <p>Проверьте соединение и попробуйте ещё раз.</p>
      <button class="button button-outline" :disabled="session.loading" @click="retry">
        {{ session.loading ? "Загружаем…" : "Попробовать снова" }}
      </button>
    </div>
    <p v-else-if="!session.user" role="status" class="muted">Загружаем ваш аккаунт…</p>
    <template v-else>
      <ProfileOverview :user="session.user" />
      <section class="security-callout" aria-labelledby="security-title">
        <div>
          <h2 id="security-title">Аккаунт и безопасность</h2>
          <p>Настройте способы входа, двухфакторную аутентификацию и passkeys. Управляйте активными сессиями.</p>
        </div>
        <a href="/accounts/" class="button">Открыть настройки</a>
      </section>
      <a href="/accounts/logout/" class="muted logout-link">Выйти из аккаунта</a>
    </template>
  </section>
</template>
