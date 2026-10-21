<script setup lang="ts">
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
defineProps<{
  pending: boolean;
  count: number;
  error: string | null;
  mode: "provider" | "file";
}>();
defineEmits<{ close: []; confirm: [] }>();
</script>
<template>
  <Dialog
    :open="true"
    @update:open="
      (value) => {
        if (!value && !pending) $emit('close');
      }
    "
    ><DialogContent
      :show-close-button="!pending"
      @escape-key-down="
        (event) => {
          if (pending) event.preventDefault();
        }
      "
      @interact-outside="
        (event) => {
          if (pending) event.preventDefault();
        }
      "
      ><DialogHeader
        ><DialogTitle>{{
          mode === "file" ? "Сформировать XML?" : "Обновить тексты публикаций?"
        }}</DialogTitle
        ><DialogDescription
          >Экспорт разрешён для {{ count }} связанных публикаций. Система
          проверит ключи и тексты и подготовит общий файл.
          {{
            mode === "file"
              ? "Вы получите ссылку для просмотра и ручного импорта. Отправка в источник не выполняется."
              : "Ссылка будет передана в источник автоматически, затем система проверит результат обновления."
          }}
          Изменения каталога после подготовки войдут в следующий
          запуск.</DialogDescription
        ></DialogHeader
      ><Alert v-if="error" variant="destructive"
        ><AlertDescription>{{ error }}</AlertDescription></Alert
      >
      <div class="flex justify-end gap-2">
        <Button variant="outline" :disabled="pending" @click="$emit('close')"
          >Отмена</Button
        ><Button :disabled="pending" @click="$emit('confirm')">{{
          pending
            ? "Запускаем…"
            : mode === "file"
              ? "Сформировать файл"
              : "Обновить публикации"
        }}</Button>
      </div></DialogContent
    ></Dialog
  >
</template>
