<script setup lang="ts">
import { UserRound, KeyRound, ShieldCheck, ArrowRight } from "@lucide/vue";
import { Button } from "@dnk/ui/components/button";
import { Alert, AlertDescription } from "@dnk/ui/components/alert";
import { Spinner } from "@dnk/ui/components/spinner";
import { useCoreSession } from "../session/model/session";
const { session, refreshSession } = useCoreSession();
const features = [
  { icon: UserRound, title: "Один профиль", description: "Ваши данные и настройки в одном месте" },
  { icon: KeyRound, title: "Удобный вход", description: "Пароль, Telegram или ключ доступа" },
  { icon: ShieldCheck, title: "Безопасность", description: "Двухфакторная защита и управление сессиями" },
];
</script>
<template>
  <section class="hero" aria-labelledby="hero-title">
    <h1 id="hero-title">dNiko Alpha — единый аккаунт для вашей работы</h1>
    <p>Управляйте профилем, способами входа и безопасностью в одном месте</p>
    <div class="hero-actions">
      <Button v-if="session.authenticated" as-child size="lg"><NuxtLink to="/app/">Открыть приложение<ArrowRight /></NuxtLink></Button>
      <template v-else>
        <Button as="a" href="/accounts/signup/?next=/app/" size="lg">Создать аккаунт<ArrowRight /></Button>
        <Button as="a" href="/accounts/login/?next=/app/" variant="outline" size="lg">Войти</Button>
      </template>
    </div>
    <Alert v-if="session.error" class="hero-session-error" role="status" aria-live="polite"><AlertDescription>
      <p>Не удалось проверить аккаунт. Попробуйте ещё раз.</p>
      <Button variant="link" :disabled="session.loading" @click="refreshSession"><Spinner v-if="session.loading" />Повторить</Button>
    </AlertDescription></Alert>
  </section>
  <section class="feature-strip" aria-label="Возможности аккаунта">
    <article v-for="feature in features" :key="feature.title">
      <component :is="feature.icon" class="size-6" aria-hidden="true" />
      <h2>{{ feature.title }}</h2><p>{{ feature.description }}</p>
    </article>
  </section>
</template>
