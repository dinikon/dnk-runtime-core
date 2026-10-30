<script setup lang="ts">
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import type { ChannelFilters, Platform } from "../model/channel.types";
defineProps<{ filters: ChannelFilters; platforms: Platform[] }>();
const emit = defineEmits<{
  filter: [key: "q" | "platform" | "status", value: string];
}>();
</script>
<template>
  <div class="flex shrink-0 flex-wrap gap-3">
    <Input
      :model-value="filters.search"
      class="sm:max-w-sm"
      aria-label="Поиск каналов"
      placeholder="Название подключения"
      @update:model-value="emit('filter', 'q', String($event))"
    />
    <NativeSelect
      :model-value="filters.platformKind"
      aria-label="Фильтр платформы"
      @update:model-value="emit('filter', 'platform', String($event))"
      ><option value="">Все платформы</option>
      <option v-for="p in platforms" :key="p.kind" :value="p.kind">
        {{ p.title }}
      </option></NativeSelect
    >
    <NativeSelect
      :model-value="filters.status"
      aria-label="Статус проверки"
      @update:model-value="emit('filter', 'status', String($event))"
      ><option value="">Все статусы</option>
      <option value="pending">Проверяем</option>
      <option value="verified">Проверено</option>
      <option value="error">Ошибка</option></NativeSelect
    >
  </div>
</template>
