<script setup lang="ts">
import { ref, watch } from "vue";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { PublicationIdentity } from "../model/publication-identity.types";
import { identityLabels } from "../model/publication-identity.presentation";
const props = defineProps<{ identity: PublicationIdentity; label: string }>();
defineEmits<{ duplicates: [key: string] }>();
const copied = ref(false),
  copyError = ref(false);
watch(
  () => props.identity.key,
  () => {
    copied.value = false;
    copyError.value = false;
  },
);
async function copyKey(): Promise<void> {
  if (props.identity.key === null) return;
  try {
    await navigator.clipboard.writeText(props.identity.key);
    copied.value = true;
    copyError.value = false;
  } catch {
    copyError.value = true;
  }
}
</script>
<template>
  <div
    v-if="identity.state !== 'not_required'"
    class="flex max-w-64 flex-col items-start gap-1"
  >
    <Badge :variant="identity.state === 'valid' ? 'outline' : 'secondary'">{{
      identityLabels[identity.state]
    }}</Badge>
    <span
      v-if="identity.key !== null && identity.key.trim()"
      class="max-w-full select-all break-all text-xs"
      >{{ identity.key }}</span
    >
    <span
      v-if="identity.state === 'missing'"
      class="text-xs text-muted-foreground"
      >Для обновления через выгрузку нужен ключ.</span
    >
    <template v-if="identity.state === 'duplicate'">
      <span class="text-xs text-muted-foreground"
        >Других публикаций с этим ключом: {{ identity.conflictCount }}</span
      >
      <Button
        v-if="identity.key !== null"
        size="sm"
        variant="link"
        class="h-auto p-0"
        @click="$emit('duplicates', identity.key)"
        >Показать дубли</Button
      >
    </template>
    <Button
      v-if="identity.key !== null && identity.key.trim()"
      size="sm"
      variant="ghost"
      class="h-auto px-0 text-xs"
      :aria-label="`Копировать ${label}`"
      @click="copyKey"
      >{{ copied ? "Скопировано" : "Копировать ключ" }}</Button
    >
    <span v-if="copyError" class="text-xs text-muted-foreground"
      >Выделите ключ и скопируйте его вручную.</span
    >
  </div>
</template>
