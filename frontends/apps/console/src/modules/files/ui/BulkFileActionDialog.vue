<script setup lang="ts">
import { computed, watch } from "vue";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import {
  useBulkFileActions,
  type BulkFileTarget,
  type BulkFileSubmit,
} from "../model/use-bulk-file-actions";

const props = defineProps<{
  target: BulkFileTarget | null;
  submit: BulkFileSubmit;
  refresh: () => Promise<void>;
}>();
const emit = defineEmits<{
  close: [];
  busy: [value: boolean];
  completed: [id: string];
}>();
const { results, running, refreshError, stopped, pending, succeeded, execute } =
  useBulkFileActions(
    computed(() => props.target),
    props.submit,
    props.refresh,
    (id) => emit("completed", id),
  );
const titles = {
  trash: "Переместить выбранные файлы в корзину?",
  restore: "Восстановить выбранные файлы?",
  purge: "Удалить выбранные файлы навсегда?",
};
const labels = {
  trash: "В корзину",
  restore: "Восстановить",
  purge: "Удалить навсегда",
};
const statuses = {
  pending: "Ожидает",
  working: "Обработка",
  success: "Готово",
  failed: "Ошибка",
};
let trigger: HTMLElement | null = null;
watch(
  () => props.target,
  (target, previous) => {
    if (target && !previous)
      trigger = document.activeElement as HTMLElement | null;
  },
  { flush: "sync" },
);
watch(running, (value) => emit("busy", value), { flush: "sync" });
function restoreFocus(event: Event): void {
  event.preventDefault();
  if (trigger?.isConnected && !trigger.matches(":disabled")) trigger.focus();
  else
    (
      document.querySelector(
        '[aria-label="Выбрать все на странице"]:not([disabled])',
      ) as HTMLElement | null
    )?.focus();
}
</script>
<template>
  <Dialog :open="!!target" @update:open="!$event && !running && emit('close')">
    <DialogContent
      lang="ru"
      class="max-h-[calc(100dvh-2rem)] overflow-y-auto sm:max-w-2xl"
      :show-close-button="!running"
      @escape-key-down="running && $event.preventDefault()"
      @interact-outside="running && $event.preventDefault()"
      @close-auto-focus="restoreFocus"
    >
      <DialogHeader>
        <DialogTitle>{{ target ? titles[target.action] : "" }}</DialogTitle>
        <DialogDescription>
          <template v-if="target?.action === 'trash'"
            >Файлы станут недоступны для связанных модулей. Их можно
            восстановить в течение 30 дней.</template
          >
          <template v-else-if="target?.action === 'restore'"
            >Выбранные файлы вернутся в активный список. Сервер проверит срок
            хранения и доступность каждого файла.</template
          >
          <template v-else
            >Все версии выбранных файлов будут окончательно удалены в фоне.
            После принятия удаления восстановить файл нельзя.</template
          >
        </DialogDescription>
      </DialogHeader>
      <p role="status" aria-live="polite" class="text-sm text-muted-foreground">
        Выбрано: {{ results.length }} · Успешно: {{ succeeded }}
      </p>
      <ul
        aria-label="Результаты массового действия"
        class="flex min-w-0 flex-col gap-2"
      >
        <li
          v-for="item in results"
          :key="item.file.file_id"
          class="min-w-0 rounded-md border p-3"
        >
          <div class="flex min-w-0 items-start justify-between gap-2">
            <span class="min-w-0 break-all text-sm">{{ item.file.name }}</span
            ><Badge
              :variant="item.status === 'failed' ? 'destructive' : 'secondary'"
              >{{ statuses[item.status] }}</Badge
            >
          </div>
          <p
            v-if="item.error"
            role="alert"
            class="mt-2 break-words text-sm text-destructive"
          >
            {{ item.error }}
          </p>
        </li>
      </ul>
      <Alert v-if="target?.action === 'purge' && succeeded"
        ><AlertDescription
          >Удаление принято. Файлы останутся в корзине со статусом «Удаляется»
          до завершения фоновой обработки.</AlertDescription
        ></Alert
      >
      <Alert v-if="stopped"
        ><AlertTitle>Обработка остановлена</AlertTitle
        ><AlertDescription
          >Оставшиеся файлы не обработаны. Проверьте состояние списка перед
          повтором.</AlertDescription
        ></Alert
      >
      <Alert v-if="refreshError" variant="destructive"
        ><AlertDescription>{{ refreshError }}</AlertDescription></Alert
      >
      <DialogFooter
        ><Button variant="outline" :disabled="running" @click="emit('close')"
          >Закрыть</Button
        ><Button
          v-if="pending.length"
          :variant="target?.action === 'restore' ? 'default' : 'destructive'"
          :disabled="running"
          @click="execute"
          ><Spinner v-if="running" />{{
            succeeded || results.some((item) => item.status === "failed")
              ? "Повторить оставшиеся"
              : target
                ? labels[target.action]
                : ""
          }}
          ({{ pending.length }})</Button
        ></DialogFooter
      >
    </DialogContent>
  </Dialog>
</template>
