import { computed, onScopeDispose, ref, watch, type Ref } from "vue";
import type { AxiosProgressEvent } from "axios";
import { getApiErrorStatus } from "@/app/providers/http";
import { fileError } from "./errors";

export const maxUploadBytes = 1024 ** 3;
export type UploadFileSubmit = (
  file: File,
  bucketId: string,
  progress: (event: AxiosProgressEvent) => void,
) => Promise<void>;
type UploadStatus =
  "queued" | "uploading" | "uploaded" | "failed" | "uncertain" | "invalid";
export interface BatchUploadItem {
  id: number;
  file: File;
  status: UploadStatus;
  progress: number;
  transferred: boolean;
  error: string;
  acknowledged: boolean;
}
export const uploadStatusLabels: Record<UploadStatus, string> = {
  queued: "В очереди",
  uploading: "Загрузка",
  uploaded: "Загружен",
  failed: "Ошибка",
  uncertain: "Результат неизвестен",
  invalid: "Превышен размер",
};

export function useUploadBatch(
  open: Ref<boolean>,
  submit: UploadFileSubmit,
  refresh: () => Promise<void>,
) {
  const items = ref<BatchUploadItem[]>([]);
  const running = ref(false);
  const stopped = ref(false);
  const refreshError = ref("");
  let generation = 0;
  let nextId = 0;
  let stopRequested = false;
  const eligible = (item: BatchUploadItem): boolean =>
    item.status === "queued" ||
    item.status === "failed" ||
    (item.status === "uncertain" && item.acknowledged);
  const pendingCount = computed(() => items.value.filter(eligible).length);
  const uploadedCount = computed(
    () => items.value.filter((item) => item.status === "uploaded").length,
  );
  const totalBytes = computed(() =>
    items.value.reduce((sum, item) => sum + item.file.size, 0),
  );
  const uncertain = computed(() =>
    items.value.some((item) => item.status === "uncertain"),
  );

  function reset(): void {
    generation++;
    stopRequested = true;
    items.value = [];
    running.value = false;
    stopped.value = false;
    refreshError.value = "";
  }

  function add(files: File[]): void {
    if (running.value) return;
    for (const file of files) {
      const invalid = file.size > maxUploadBytes;
      items.value.push({
        id: nextId++,
        file,
        status: invalid ? "invalid" : "queued",
        progress: 0,
        transferred: false,
        acknowledged: false,
        error: invalid
          ? "Файл больше 1 ГиБ. Выберите файл меньшего размера."
          : "",
      });
    }
  }

  function remove(id: number): void {
    if (!running.value)
      items.value = items.value.filter((item) => item.id !== id);
  }

  function stop(): void {
    stopRequested = true;
  }

  async function upload(bucketId: string): Promise<void> {
    if (running.value || !bucketId || !pendingCount.value) return;
    const batch = items.value.filter(eligible);
    const current = generation;
    stopRequested = false;
    stopped.value = false;
    refreshError.value = "";
    running.value = true;
    try {
      for (const item of batch) {
        if (generation !== current) return;
        if (stopRequested) break;
        item.status = "uploading";
        item.error = "";
        item.progress = 0;
        item.transferred = false;
        item.acknowledged = false;
        try {
          await submit(item.file, bucketId, (event) => {
            if (generation !== current) return;
            if (event.total)
              item.progress = Math.min(
                100,
                Math.round((event.loaded / event.total) * 100),
              );
            item.transferred = !!event.total && event.loaded >= event.total;
          });
          if (generation !== current) return;
          item.status = "uploaded";
          item.progress = 100;
        } catch (cause) {
          if (generation !== current) return;
          const status = getApiErrorStatus(cause);
          const ambiguous = status === null || status === 408 || status >= 500;
          item.status = ambiguous ? "uncertain" : "failed";
          item.error = fileError(cause);
          if (ambiguous || status === 401 || status === 403 || status === 429)
            stopRequested = true;
        }
      }
      if (generation !== current) return;
      stopped.value = stopRequested && pendingCount.value > 0;
      // Сбой обновления списка не отменяет подтверждённые сервером загрузки.
      try {
        await refresh();
      } catch {
        if (generation === current)
          refreshError.value =
            "Не удалось обновить список. Проверьте его кнопкой «Обновить» после закрытия окна.";
      }
    } finally {
      if (generation === current) running.value = false;
    }
  }

  watch(open, reset, { flush: "sync" });
  onScopeDispose(reset);
  return {
    items,
    running,
    stopped,
    refreshError,
    pendingCount,
    uploadedCount,
    totalBytes,
    uncertain,
    add,
    remove,
    stop,
    upload,
  };
}
