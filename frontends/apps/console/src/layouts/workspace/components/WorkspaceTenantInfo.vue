<script setup lang="ts">
import { computed, onMounted } from "vue";

import { useTenantStore } from "@/app/stores/tenant";

const tenantStore = useTenantStore();
const props = defineProps<{
  subtitle?: string;
}>();

const tenantName = computed(() => tenantStore.tenantName);
const tenantStatus = computed(() =>
  tenantStore.isResolvingTenant && !tenantStore.tenant
    ? "loading"
    : tenantStore.tenantStatus,
);
const tenantSubtitle = computed(
  () => props.subtitle ?? `Status: ${tenantStatus.value}`,
);

onMounted(() => {
  if (!tenantStore.tenant && !tenantStore.isResolvingTenant) {
    void tenantStore.resolveTenant();
  }
});
</script>

<template>
  <div class="grid flex-1 text-left text-sm leading-tight">
    <span class="truncate font-medium">{{ tenantName }}</span>
    <span class="truncate text-xs text-muted-foreground">{{
      tenantSubtitle
    }}</span>
  </div>
</template>
