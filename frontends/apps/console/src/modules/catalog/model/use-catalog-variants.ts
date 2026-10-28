import { computed, ref, watch, type Ref, type ComputedRef } from "vue";
import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryReturnType,
} from "@tanstack/vue-query";
import axios from "axios";
import { catalogApi } from "../api/catalog.api";
import type { CatalogItemsPage } from "./catalog.types";
import { getApiErrorMessage } from "@/app/providers/http";

export interface VariantPagination {
  offset: number;
  limit: number;
}
export function useCatalogVariants(
  rootId: Ref<string>,
  tenantId: Ref<string>,
  sessionKey: Ref<string>,
  locale: Ref<string>,
  pagination: Ref<VariantPagination>,
): UseQueryReturnType<CatalogItemsPage, Error> {
  return useQuery({
    queryKey: computed(() => [
      "catalog",
      tenantId.value,
      sessionKey.value,
      "variants",
      rootId.value,
      locale.value,
      pagination.value,
    ]),
    enabled: computed(
      () => !!rootId.value && !!tenantId.value && !!locale.value,
    ),
    queryFn: ({ signal }) =>
      catalogApi.listVariants(
        rootId.value,
        locale.value,
        pagination.value.offset,
        pagination.value.limit,
        signal,
      ),
  });
}
interface VariantMutationState {
  pending: ComputedRef<boolean>;
  error: ComputedRef<string>;
  uncertain: Ref<boolean>;
  create(): Promise<string | null>;
  remove(id: string): Promise<boolean>;
  reset(): void;
}
export function useCatalogVariantMutations(
  rootId: Ref<string>,
  tenantId: Ref<string>,
  sessionKey: Ref<string>,
): VariantMutationState {
  const cache = useQueryClient();
  const uncertain = ref(false);
  const createAction = useMutation({
    mutationFn: (id: string) => catalogApi.createVariant(id),
    retry: false,
  });
  const deleteAction = useMutation({
    mutationFn: ({ root, id }: { root: string; id: string }) =>
      catalogApi.deleteVariant(root, id),
    retry: false,
  });
  const scope = () => `${sessionKey.value}:${rootId.value}`;
  const pending = computed(
    () => createAction.isPending.value || deleteAction.isPending.value,
  );
  const error = computed(() =>
    uncertain.value
      ? "Ответ на создание не получен. Вариант мог быть создан. Обновите список перед новой попыткой."
      : createAction.error.value || deleteAction.error.value
        ? getApiErrorMessage(
            createAction.error.value ?? deleteAction.error.value,
            "Не удалось изменить варианты.",
          )
        : "",
  );
  function reset(): void {
    createAction.reset();
    deleteAction.reset();
    uncertain.value = false;
  }
  watch([rootId, sessionKey], reset);
  async function create(): Promise<string | null> {
    if (pending.value || uncertain.value) return null;
    const captured = scope(),
      tenant = tenantId.value,
      id = rootId.value;
    try {
      const result = await createAction.mutateAsync(id);
      if (scope() !== captured) return null;
      await cache.invalidateQueries({ queryKey: ["catalog", tenant] });
      return scope() === captured ? result.id : null;
    } catch (error: unknown) {
      if (scope() === captured)
        uncertain.value =
          !axios.isAxiosError(error) ||
          !error.response ||
          error.response.status >= 500;
      return null;
    }
  }
  async function remove(id: string): Promise<boolean> {
    if (pending.value) return false;
    const captured = scope(),
      tenant = tenantId.value,
      root = rootId.value;
    try {
      await deleteAction.mutateAsync({ root, id });
      if (scope() !== captured) return false;
      await cache.invalidateQueries({ queryKey: ["catalog", tenant] });
      return scope() === captured;
    } catch {
      return false;
    }
  }
  return { pending, error, uncertain, create, remove, reset };
}
