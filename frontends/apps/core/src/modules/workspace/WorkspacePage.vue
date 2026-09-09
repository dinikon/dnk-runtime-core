<script setup lang="ts">
import { Button } from "@dnk/ui/components/button";
import { Alert, AlertTitle, AlertDescription } from "@dnk/ui/components/alert";
import { Avatar, AvatarFallback } from "@dnk/ui/components/avatar";
import { Skeleton } from "@dnk/ui/components/skeleton";
import { Spinner } from "@dnk/ui/components/spinner";
import { computed } from "vue";
import { useRoute } from "#imports";
import { loginUrl, useCoreSession } from "../session/model/session";
import ProfileOverview from "./ui/ProfileOverview.vue";

const route = useRoute();
const { session, refreshSession } = useCoreSession();
const displayName = computed(() =>
  session.value.user?.display_name || "Ваш аккаунт",
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
      <Avatar class="mb-5 size-14"><AvatarFallback>{{ session.user?.initials || "АК" }}</AvatarFallback></Avatar>
      <h1 id="workspace-title">{{ displayName }}</h1>
      <p class="muted">Профиль и настройки вашего аккаунта dNiko Alpha.</p>
    </header>
    <Alert v-if="session.error" role="alert">
      <AlertTitle><h2>Не удалось загрузить аккаунт</h2></AlertTitle>
      <AlertDescription><p>Проверьте соединение и попробуйте ещё раз.</p>
      <Button variant="outline" class="mt-4" :disabled="session.loading" @click="retry">
        <Spinner v-if="session.loading" />{{ session.loading ? "Загружаем…" : "Попробовать снова" }}
      </Button></AlertDescription>
    </Alert>
    <div v-else-if="!session.user" role="status" class="flex flex-col gap-4"><span class="sr-only">Загружаем ваш аккаунт…</span><Skeleton v-for="row in 4" :key="row" class="h-12 w-full" /></div>
    <template v-else>
      <ProfileOverview :user="session.user" />
      <section class="security-callout" aria-labelledby="security-title">
        <div>
          <h2 id="security-title">Аккаунт и безопасность</h2>
          <p>Настройте способы входа, двухфакторную аутентификацию и passkeys. Управляйте активными сессиями.</p>
        </div>
        <Button as="a" href="/accounts/">Открыть настройки</Button>
      </section>
      <a href="/accounts/logout/" class="muted logout-link">Выйти из аккаунта</a>
    </template>
  </section>
</template>
