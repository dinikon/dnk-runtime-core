import { onBeforeUnmount, reactive, ref } from "vue";
import { isNavigationFailure } from "vue-router";
import { useQueryClient } from "@tanstack/vue-query";
import axios from "axios";
import { getApiErrorMessage } from "@/app/providers/http";
import { catalogApi } from "../api/catalog.api";
import { useCatalogContext } from "./use-catalog-context";
import {
  ProductCreation,
  productCreationState,
  type ProductPreset,
} from "./product-creation";

/** Общее создание из списка и прямой ссылки, с границей tenant/session. */
export function useCreateCatalogItem(
  direct = false,
  busy: () => boolean = () => false,
) {
  const state = reactive(productCreationState());
  const open = ref(direct);
  const navigating = ref(false);
  const cache = useQueryClient();
  const ctx = useCatalogContext(
    () => false,
    () => busy() || (state.pending && !navigating.value),
    () => {
      creation.cancel();
      open.value = direct;
    },
  );
  const creation = new ProductCreation(
    state,
    (virtual, kind) => catalogApi.createItem(virtual, kind),
    async (id) => {
      const current = ctx.captureSession();
      await cache.invalidateQueries({
        queryKey: ["catalog", ctx.tenantId.value],
        refetchType: "none",
      });
      if (!current()) return;
      navigating.value = true;
      try {
        const target = {
          path: `/catalog/items/${encodeURIComponent(id)}`,
          query: { locale: ctx.locale.value, focus: "title" },
        };
        const result = await (direct
          ? ctx.router.replace(target)
          : ctx.router.push(target));
        if (isNavigationFailure(result)) throw new Error("Переход отменён");
      } finally {
        navigating.value = false;
      }
    },
    (error) => ({
      message: getApiErrorMessage(
        error,
        "Не удалось создать товар. Попробуйте ещё раз.",
      ),
      uncertain:
        !axios.isAxiosError(error) ||
        !error.response ||
        error.response.status >= 500,
    }),
  );
  onBeforeUnmount(() => creation.cancel());
  function choose(preset: ProductPreset): void {
    if (ctx.active.value) void creation.create(preset);
  }
  function show(): void {
    creation.cancel();
    open.value = true;
  }
  function close(): void {
    if (state.pending) return;
    open.value = false;
    if (direct)
      void ctx.router.replace({
        path: "/catalog/items",
        query: { locale: ctx.locale.value },
      });
  }
  function checkCatalog(): void {
    close();
    void cache.invalidateQueries({ queryKey: ["catalog", ctx.tenantId.value] });
  }
  return { ctx, state, open, show, close, choose, checkCatalog };
}
