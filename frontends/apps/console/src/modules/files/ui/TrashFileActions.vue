<script setup lang="ts">
import { computed } from "vue";
import { useNow } from "@vueuse/core";
import { RotateCcw, Trash2 } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { TrashFileItem } from "../model/types";
const props = defineProps<{ file: TrashFileItem; busy: boolean }>();
defineEmits<{ restore: [file: TrashFileItem]; purge: [file: TrashFileItem] }>();
const now = useNow({ interval: 1000 });
const expired = computed(
  () => new Date(props.file.purge_after).getTime() <= now.value.getTime(),
);
</script>
<template>
  <div v-if="file.status === 'purging'" class="flex flex-col items-start gap-1">
    <Badge variant="secondary">Удаляется</Badge
    ><span class="text-xs text-muted-foreground">Ожидает завершения</span>
  </div>
  <div v-else class="flex flex-wrap items-center gap-1">
    <Button
      variant="outline"
      size="sm"
      :disabled="busy || expired"
      :aria-label="`Восстановить: ${file.name}`"
      @click="$emit('restore', file)"
      ><RotateCcw data-icon="inline-start" />Восстановить</Button
    ><Button
      variant="ghost"
      size="sm"
      :disabled="busy"
      :aria-label="`Удалить навсегда: ${file.name}`"
      @click="$emit('purge', file)"
      ><Trash2 data-icon="inline-start" />Удалить навсегда</Button
    ><span v-if="expired" class="w-full text-xs text-muted-foreground"
      >Срок восстановления истёк</span
    >
  </div>
</template>
