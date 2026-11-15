<script setup lang="ts">
import { Button } from "@/components/ui/button";
defineProps<{
  loading: boolean;
  error: string;
  executable: boolean;
  hasDraft: boolean;
  conflict: boolean;
  uncertain: boolean;
  expectedVersion: number;
  serverVersion: number;
  refreshDisabled: boolean;
  acceptDisabled: boolean;
}>();
const emit = defineEmits<{ retry: []; accept: [] }>();
</script>
<template>
  <p v-if="loading" role="status">Загрузка оставшегося плана…</p>
  <div
    v-if="error"
    role="alert"
    class="shrink-0 rounded-md border border-destructive p-3 text-sm text-destructive"
  >
    {{ error
    }}<Button
      variant="outline"
      :disabled="refreshDisabled"
      @click="emit('retry')"
      >Повторить</Button
    >
  </div>
  <p
    v-if="hasDraft && !executable && !uncertain"
    role="alert"
    class="text-sm text-destructive"
  >
    Текущий статус документа не допускает возврат. Введённый факт сохранён для
    сверки.
  </p>
  <div
    v-if="conflict && !uncertain"
    role="alert"
    class="shrink-0 rounded-md bg-muted p-3 text-sm"
  >
    Конфликт версии: форма {{ expectedVersion }}, сервер {{ serverVersion }}.
    Ввод сохранён. Проверьте новые остатки перед продолжением.
    <div class="mt-2 flex flex-wrap gap-2">
      <Button
        variant="outline"
        :disabled="refreshDisabled"
        @click="emit('retry')"
        >Загрузить актуальный план</Button
      ><Button
        variant="outline"
        :disabled="acceptDisabled"
        @click="emit('accept')"
        >Принять новую версию, сохранив ввод</Button
      >
    </div>
  </div>
  <p
    v-if="uncertain"
    role="alert"
    class="shrink-0 rounded-md bg-muted p-3 text-sm"
  >
    Результат запроса неизвестен. Повтор исходной команды с прежним ключом не
    создаст второй факт. Поля сохранены и заблокированы.
  </p>
</template>
