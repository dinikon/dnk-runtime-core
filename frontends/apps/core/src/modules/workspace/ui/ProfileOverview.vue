<script setup lang="ts">
import type { CoreUser } from "../../session/model/session";

defineProps<{ user: CoreUser }>();
</script>

<template>
  <section class="profile-section" aria-labelledby="profile-title">
    <h2 id="profile-title">Профиль</h2>
    <dl class="detail-list">
      <div><dt>Имя пользователя</dt><dd>{{ user.username }}</dd></div>
      <div><dt>Email</dt><dd>{{ user.email || "Не указан" }}</dd></div>
      <div><dt>Имя</dt><dd>{{ user.first_name || "Не указано" }}</dd></div>
      <div><dt>Фамилия</dt><dd>{{ user.last_name || "Не указана" }}</dd></div>
    </dl>
  </section>
</template>
