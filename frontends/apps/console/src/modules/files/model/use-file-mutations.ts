import { computed, onScopeDispose, watch } from "vue";
import { useMutation, useQueryClient } from "@tanstack/vue-query";
import type { AxiosProgressEvent } from "axios";
import { toast } from "vue-sonner";
import { useTenantStore } from "@/app/stores/tenant";
import { filesApi } from "../api/files.api";
import { filesKeys } from "./query-keys";
export function useFileMutations() {
  const store = useTenantStore();
  const client = useQueryClient();
  const tenant = computed(() => store.tenant?.tenant_id ?? "");
  let controller = new AbortController();
  function abort(): void {
    controller.abort();
    controller = new AbortController();
  }
  watch(tenant, abort);
  onScopeDispose(abort);
  async function refresh(id: string): Promise<void> {
    await client.invalidateQueries({ queryKey: filesKeys.tenant(id) });
  }
  function signal(id: string): AbortSignal {
    if (!id || id !== tenant.value)
      throw new Error("Рабочее пространство изменилось. Обновите страницу.");
    return controller.signal;
  }
  const upload = useMutation({
    retry: false,
    mutationFn: (input: {
      tenant: string;
      file: File;
      bucketId: string;
      onProgress: (event: AxiosProgressEvent) => void;
    }) =>
      filesApi.upload(
        input.file,
        input.bucketId,
        input.onProgress,
        signal(input.tenant),
      ),
    onSuccess: async (_, input) => {
      if (tenant.value === input.tenant) toast.success("Файл загружен");
      await refresh(input.tenant);
    },
  });
  const trash = useMutation({
    retry: false,
    mutationFn: (input: { tenant: string; id: string }) =>
      filesApi.trash(input.id, signal(input.tenant)),
    onSuccess: async (_, input) => {
      if (tenant.value === input.tenant)
        toast.success("Файл перемещён в корзину");
      await refresh(input.tenant);
    },
  });
  const restore = useMutation({
    retry: false,
    mutationFn: (input: { tenant: string; id: string }) =>
      filesApi.restore(input.id, signal(input.tenant)),
    onSuccess: async (_, input) => {
      if (tenant.value === input.tenant) toast.success("Файл восстановлен");
      await refresh(input.tenant);
    },
  });
  const purge = useMutation({
    retry: false,
    mutationFn: (input: { tenant: string; id: string }) =>
      filesApi.purge(input.id, signal(input.tenant)),
    onSuccess: async (_, input) => {
      if (tenant.value === input.tenant)
        toast.success("Файл поставлен на окончательное удаление");
      await refresh(input.tenant);
    },
  });
  return { upload, trash, restore, purge, refresh };
}
