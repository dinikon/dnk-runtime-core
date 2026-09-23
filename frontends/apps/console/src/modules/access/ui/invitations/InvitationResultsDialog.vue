<script setup lang="ts">
import { Check, Copy, TriangleAlert } from "@lucide/vue";
import { computed } from "vue";
import { toast } from "vue-sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import type { InvitationResult } from "../../model/access.types";

const props = defineProps<{
  open: boolean;
  results: InvitationResult[];
}>();
const emit = defineEmits<{
  "update:open": [value: boolean];
}>();

const successful = computed(() => props.results.filter((result) => result.ok));

async function copy(value: string) {
  await navigator.clipboard.writeText(value);
  toast.success("Ссылка скопирована");
}

async function copyAll() {
  const value = successful.value
    .map((result) => `${result.email}: ${result.invitationUrl}`)
    .join("\n");
  await copy(value);
}
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent class="sm:max-w-2xl">
      <DialogHeader>
        <DialogTitle>Результаты приглашения</DialogTitle>
        <DialogDescription>
          Скопируйте приватные ссылки сейчас — после закрытия окна получить их
          повторно нельзя.
        </DialogDescription>
      </DialogHeader>
      <div class="grid max-h-[55vh] gap-3 overflow-y-auto pr-1">
        <div
          v-for="result in results"
          :key="result.email"
          class="grid gap-2 rounded-lg border p-3"
        >
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="flex min-w-0 items-center gap-2">
              <Check v-if="result.ok" class="size-4 text-emerald-600" />
              <TriangleAlert v-else class="size-4 text-destructive" />
              <span class="truncate font-medium">{{ result.email }}</span>
            </div>
            <Badge :variant="result.ok ? 'secondary' : 'destructive'">
              {{ result.ok ? "Создано" : "Ошибка" }}
            </Badge>
          </div>
          <div v-if="result.invitationUrl" class="flex gap-2">
            <Input :model-value="result.invitationUrl" readonly />
            <Button
              variant="outline"
              size="icon"
              aria-label="Скопировать ссылку"
              @click="copy(result.invitationUrl)"
            >
              <Copy />
            </Button>
          </div>
          <p v-else class="text-sm text-destructive">{{ result.message }}</p>
        </div>
      </div>
      <DialogFooter>
        <Button v-if="successful.length > 1" variant="outline" @click="copyAll">
          <Copy />
          Скопировать все
        </Button>
        <Button @click="emit('update:open', false)">Готово</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
