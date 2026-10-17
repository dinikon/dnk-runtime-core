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
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useFilePreview } from "../model/use-file-preview";
import { formatStorageBytes, type FileItem } from "../model/types";

const props = defineProps<{ file: FileItem | null; tenant: string }>();
defineEmits<{ close: [] }>();
let trigger: HTMLElement | null = null;
watch(
  () => props.file,
  (file, previous) => {
    if (file && !previous)
      trigger = document.activeElement as HTMLElement | null;
  },
  { flush: "sync" },
);
function restoreFocus(event: Event): void {
  event.preventDefault();
  if (trigger?.isConnected) trigger.focus();
}
const { loading, error, url, text, truncated, kind, load, mediaFailed } =
  useFilePreview(
    computed(() => props.file),
    computed(() => props.tenant),
  );
</script>
<template>
  <Dialog :open="!!file" @update:open="!$event && $emit('close')">
    <DialogContent
      lang="ru"
      class="flex max-h-[90dvh] min-w-0 flex-col sm:max-w-5xl"
      :show-close-button="false"
      @close-auto-focus="restoreFocus"
    >
      <DialogHeader class="min-w-0">
        <DialogTitle>Предпросмотр файла</DialogTitle>
        <DialogDescription class="break-all">
          {{ file?.name }} · {{ formatStorageBytes(file?.size_bytes ?? 0) }}
        </DialogDescription>
      </DialogHeader>
      <div
        v-if="loading"
        role="status"
        aria-live="polite"
        class="flex min-h-0 flex-col gap-3"
      >
        <p class="text-sm text-muted-foreground">Загрузка предпросмотра…</p>
        <Skeleton class="h-[50dvh] w-full" />
      </div>
      <Alert v-else-if="error" variant="destructive" role="alert">
        <AlertTitle>Предпросмотр недоступен</AlertTitle>
        <AlertDescription>{{ error }}</AlertDescription>
      </Alert>
      <div
        v-else-if="kind"
        class="min-h-0 overflow-auto rounded-md border bg-muted/30"
      >
        <img
          v-if="kind === 'image'"
          :src="url"
          :alt="file?.name"
          class="mx-auto max-h-[65dvh] max-w-full object-contain"
          @error="mediaFailed"
        />
        <iframe
          v-else-if="kind === 'pdf'"
          :src="url"
          :title="`Предпросмотр PDF: ${file?.name}`"
          referrerpolicy="no-referrer"
          class="h-[60dvh] w-full"
        />
        <template v-else-if="kind === 'text'">
          <p v-if="truncated" class="p-4 text-sm text-muted-foreground">
            Показаны первые 256 КиБ текста.
          </p>
          <pre class="whitespace-pre-wrap break-words p-4 text-sm">{{
            text || "Файл пуст."
          }}</pre>
        </template>
        <video
          v-else-if="kind === 'video'"
          :src="url"
          controls
          playsinline
          preload="metadata"
          :aria-label="file?.name"
          class="mx-auto max-h-[65dvh] w-full"
          @error="mediaFailed"
        />
        <audio
          v-else-if="kind === 'audio'"
          :src="url"
          controls
          preload="metadata"
          :aria-label="file?.name"
          class="w-full p-4"
          @error="mediaFailed"
        />
      </div>
      <DialogFooter>
        <Button v-if="error" variant="outline" @click="load">Повторить</Button>
        <Button variant="outline" @click="$emit('close')">Закрыть</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
