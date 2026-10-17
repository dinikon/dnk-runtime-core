<script setup lang="ts">
defineProps<{
  selected: boolean;
  loading: boolean;
  error: string;
  empty: boolean;
  filtered: boolean;
}>();
defineEmits<{ retry: [] }>();
</script>
<template>
  <div
    v-if="!selected"
    class="rounded-lg border border-dashed p-10 text-center text-muted-foreground"
  >
    Выберите язык для чтения каталога.
  </div>
  <p v-else-if="loading" role="status" class="p-8">Загрузка…</p>
  <div v-else-if="error" role="alert" class="rounded-lg border p-6">
    <p>{{ error }}</p>
    <button class="mt-3 underline" @click="$emit('retry')">Повторить</button>
  </div>
  <div
    v-else-if="empty"
    class="rounded-lg border border-dashed p-10 text-center"
  >
    <p>
      {{
        filtered
          ? "По вашему запросу ничего не найдено."
          : "Здесь пока нет записей."
      }}
    </p>
  </div>
  <slot v-else />
</template>
