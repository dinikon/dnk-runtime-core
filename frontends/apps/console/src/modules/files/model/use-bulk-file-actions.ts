import { computed, onScopeDispose, ref, watch, type Ref } from "vue";
import { getApiErrorStatus } from "@/app/providers/http";
import { fileError } from "./errors";
import type { FileItem } from "./types";

export type BulkFileAction = "trash" | "restore" | "purge";
export interface BulkFileTarget {
  action: BulkFileAction;
  files: FileItem[];
}
export type BulkFileSubmit = (
  action: BulkFileAction,
  id: string,
) => Promise<void>;
interface BulkFileResult {
  file: FileItem;
  status: "pending" | "working" | "success" | "failed";
  error: string;
}

export function useBulkFileActions(
  target: Ref<BulkFileTarget | null>,
  submit: BulkFileSubmit,
  refresh: () => Promise<void>,
  completed: (id: string) => void,
) {
  const results = ref<BulkFileResult[]>([]);
  const running = ref(false);
  const refreshError = ref("");
  const stopped = ref(false);
  let generation = 0;
  const pending = computed(() =>
    results.value.filter(
      (item) => item.status === "pending" || item.status === "failed",
    ),
  );
  const succeeded = computed(
    () => results.value.filter((item) => item.status === "success").length,
  );
  function reset(): void {
    generation++;
    running.value = false;
    refreshError.value = "";
    stopped.value = false;
    results.value =
      target.value?.files.map((file) => ({
        file,
        status: "pending",
        error: "",
      })) ?? [];
  }
  async function execute(): Promise<void> {
    if (running.value || !target.value || !pending.value.length) return;
    const action = target.value.action;
    const current = generation;
    const batch = [...pending.value];
    running.value = true;
    stopped.value = false;
    refreshError.value = "";
    try {
      for (const item of batch) {
        if (generation !== current) return;
        item.status = "working";
        item.error = "";
        try {
          await submit(action, item.file.file_id);
          if (generation !== current) return;
          item.status = "success";
          completed(item.file.file_id);
        } catch (cause) {
          if (generation !== current) return;
          item.status = "failed";
          item.error = fileError(cause);
          const status = getApiErrorStatus(cause);
          if (
            status === null ||
            status === 408 ||
            status === 401 ||
            status === 403 ||
            status === 429 ||
            status >= 500
          ) {
            stopped.value = true;
            break;
          }
        }
      }
      if (generation !== current) return;
      try {
        await refresh();
      } catch {
        if (generation === current)
          refreshError.value =
            "Не удалось обновить список. Закройте окно и нажмите «Обновить».";
      }
    } finally {
      if (generation === current) running.value = false;
    }
  }
  watch(target, reset, { immediate: true, flush: "sync" });
  onScopeDispose(() => {
    generation++;
  });
  return {
    results,
    running,
    refreshError,
    stopped,
    pending,
    succeeded,
    execute,
  };
}
