<script setup lang="ts">
import {computed} from "vue";
import {useRoute} from "vue-router";

import {SettingsLayout} from "@/layouts";

interface SettingsRouteMeta {
  settingsTitle?: string;
  settingsActiveItem?: string;
  settingsBreadcrumbs?: Array<{ label: string; to?: string }>;
}

const route = useRoute();
const settingsMeta = computed(() => route.meta as SettingsRouteMeta);
const title = computed(() => settingsMeta.value.settingsTitle ?? "Settings");
const activeItem = computed(() => settingsMeta.value.settingsActiveItem ?? "");
const breadcrumbs = computed(() => settingsMeta.value.settingsBreadcrumbs ?? [{label: title.value}]);
</script>

<template>
  <SettingsLayout
      :title="title"
      :active-item="activeItem"
      :breadcrumbs="breadcrumbs"
  >
    <div class="grid gap-2">
      <h1 class="text-base font-semibold text-neutral-900">{{ title }}</h1>
      <p class="text-sm text-neutral-400">This settings section is not available yet.</p>
    </div>
  </SettingsLayout>
</template>
