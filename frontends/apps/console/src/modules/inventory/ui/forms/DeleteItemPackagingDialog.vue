<script setup lang="ts">
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import type { ItemPackaging } from "../../model/item-packaging.types";
defineProps<{
  item: ItemPackaging;
  sku?: string;
  dirty?: boolean;
  pending: boolean;
  uncertain: boolean;
  error: string;
}>();
const emit = defineEmits<{ close: []; confirm: []; check: [] }>();
</script>
<template>
  <AlertDialog :open="true" @update:open="!$event && !pending && emit('close')">
    <AlertDialogContent
      class="max-h-[calc(100dvh-2rem)] overflow-y-auto"
      :aria-busy="pending"
      @escape-key-down="pending && $event.preventDefault()"
    >
      <AlertDialogHeader>
        <AlertDialogTitle>Удалить упаковку?</AlertDialogTitle>
        <AlertDialogDescription
          >Вариант упаковки будет удалён без возможности восстановления. SKU и
          его штрихкоды сохранятся.</AlertDialogDescription
        >
      </AlertDialogHeader>
      <dl
        class="grid min-w-0 grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-2 text-sm"
      >
        <template v-if="sku"
          ><dt class="text-muted-foreground">SKU</dt>
          <dd class="break-all">{{ sku }}</dd></template
        >
        <dt class="text-muted-foreground">Код</dt>
        <dd class="break-all font-mono">{{ item.code }}</dd>
        <dt class="text-muted-foreground">Название</dt>
        <dd class="break-all">{{ item.name }}</dd>
        <dt class="text-muted-foreground">Содержимое</dt>
        <dd class="break-all">
          {{ item.contentQuantity }} {{ item.contentUom }}
        </dd>
      </dl>
      <Alert v-if="dirty"
        ><AlertDescription
          >Несохранённые изменения будут потеряны после удаления
          упаковки.</AlertDescription
        ></Alert
      >
      <Alert v-if="error" variant="destructive"
        ><AlertDescription>{{ error }}</AlertDescription></Alert
      >
      <AlertDialogFooter>
        <AlertDialogCancel :disabled="pending" @click="emit('close')"
          >Отмена</AlertDialogCancel
        >
        <Button
          v-if="uncertain"
          type="button"
          variant="outline"
          :disabled="pending"
          @click="emit('check')"
          ><Spinner
            v-if="pending"
            data-icon="inline-start"
            aria-hidden="true"
          />Проверить наличие</Button
        >
        <Button
          v-else
          type="button"
          variant="destructive"
          :disabled="pending"
          @click="emit('confirm')"
          ><Spinner
            v-if="pending"
            data-icon="inline-start"
            aria-hidden="true"
          />{{ pending ? "Удаление…" : "Удалить упаковку" }}</Button
        >
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>
