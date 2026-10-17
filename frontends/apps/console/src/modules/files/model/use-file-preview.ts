import { onScopeDispose, ref, watch, type Ref } from "vue";
import { getApiErrorStatus } from "@/app/providers/http";
import { filesApi } from "../api/files.api";
import { fileError } from "./errors";
import type { FileItem } from "./types";

type PreviewKind = "image" | "pdf" | "text" | "audio" | "video";
const textLimit = 256 * 1024;
const imageTypes = new Set([
  "image/png",
  "image/jpeg",
  "image/gif",
  "image/webp",
  "image/avif",
  "image/bmp",
]);

export function useFilePreview(
  file: Ref<FileItem | null>,
  tenant: Ref<string>,
) {
  const loading = ref(false);
  const error = ref("");
  const url = ref("");
  const text = ref("");
  const truncated = ref(false);
  const kind = ref<PreviewKind | null>(null);
  let request: AbortController | null = null;

  function cleanup(): void {
    request?.abort();
    request = null;
    if (url.value) URL.revokeObjectURL(url.value);
    url.value = "";
    text.value = "";
    kind.value = null;
    error.value = "";
    loading.value = false;
    truncated.value = false;
  }

  async function load(): Promise<void> {
    cleanup();
    if (!file.value || !tenant.value) return;
    const controller = new AbortController();
    request = controller;
    loading.value = true;
    try {
      const blob = await filesApi.preview(
        file.value.file_id,
        controller.signal,
      );
      if (controller.signal.aborted || request !== controller) return;
      const mime = blob.type.split(";")[0]?.trim().toLowerCase();
      let previewKind: PreviewKind;
      if (mime === "text/plain") previewKind = "text";
      else if (mime === "application/pdf") previewKind = "pdf";
      else if (mime && imageTypes.has(mime)) previewKind = "image";
      else if (mime?.startsWith("audio/")) previewKind = "audio";
      else if (mime?.startsWith("video/")) previewKind = "video";
      else {
        error.value = "Предпросмотр этого формата не поддерживается.";
        return;
      }
      if (previewKind === "text") {
        const content = await blob.slice(0, textLimit).text();
        if (controller.signal.aborted || request !== controller) return;
        text.value = content;
        truncated.value = blob.size > textLimit;
      } else {
        url.value = URL.createObjectURL(blob);
      }
      kind.value = previewKind;
    } catch (cause) {
      if (controller.signal.aborted || request !== controller) return;
      const status = getApiErrorStatus(cause);
      error.value =
        status === 415
          ? "Предпросмотр этого формата не поддерживается."
          : status === 409
            ? "Не удалось подтвердить принадлежность файла рабочему пространству."
            : fileError(cause);
    } finally {
      if (request === controller) loading.value = false;
    }
  }

  function mediaFailed(event: Event): void {
    const element = event.target as HTMLImageElement | HTMLMediaElement | null;
    if (!url.value || element?.src !== url.value) return;
    error.value =
      "Браузер не смог показать файл. Возможно, файл повреждён или его кодек не поддерживается.";
  }

  watch(file, () => void load(), { immediate: true, flush: "sync" });
  watch(tenant, cleanup, { flush: "sync" });
  onScopeDispose(cleanup);
  return { loading, error, url, text, truncated, kind, load, mediaFailed };
}
