<script setup lang="ts">
import {storeToRefs} from "pinia";

import {useSessionStore} from "@/app/stores/session";

const sessionStore = useSessionStore();
const {isAuthenticated, isLoading, user} = storeToRefs(sessionStore);
</script>

<template>
  <section class="page-stack">
    <div>
      <p class="eyebrow">Workspace</p>
      <h1>Console</h1>
      <p class="lede">
        Administrative workspace for tenant operations, authentication and runtime data.
      </p>
    </div>

    <div class="status-panel">
      <span class="status-label">Session</span>
      <strong v-if="isLoading">Loading</strong>
      <strong v-else-if="isAuthenticated">{{ user?.email }}</strong>
      <strong v-else>Anonymous</strong>
    </div>
  </section>
</template>
