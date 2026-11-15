<script setup lang="ts">
defineProps<{ value: string; error?: string; disabled: boolean }>();
const emit = defineEmits<{ change: [value: string] }>();
</script>
<template>
  <label class="flex flex-col gap-2 text-sm"
    >Причина изменения состояния<textarea
      aria-label="Причина изменения состояния"
      :value="value"
      :disabled="disabled"
      required
      maxlength="1000"
      rows="3"
      class="min-h-24 w-full rounded-md border bg-background px-3 py-2"
      :aria-invalid="!!error"
      @input="emit('change', ($event.target as HTMLTextAreaElement).value)"
    /><span v-if="error" role="alert" class="text-destructive">{{ error }}</span
    ><span class="text-xs text-muted-foreground"
      >Обязательна. После подтверждения документа причина фиксируется.</span
    ></label
  >
</template>
