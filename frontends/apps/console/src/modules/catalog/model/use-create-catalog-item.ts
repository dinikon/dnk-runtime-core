import { computed } from "vue";
import {
  useInventorySkuSearch,
  type InventorySkuOption,
  type InventorySkuSearch,
} from "@/modules/inventory";
import type { CatalogSkuSelection } from "./catalog-sku.types";
import {
  onBeforeUnmount,
  reactive,
  ref,
  type Ref,
  type ComputedRef,
} from "vue";
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
  type ProductCreationState,
} from "./product-creation";

interface CatalogCreation {
  ctx: ReturnType<typeof useCatalogContext>;
  state: ProductCreationState;
  open: Ref<boolean>;
  preset: Ref<ProductPreset | null>;
  skuSearch: InventorySkuSearch;
  skuCode: Ref<string | null>;
  skuId: ComputedRef<string | null>;
  show(): void;
  close(): void;
  choose(value: ProductPreset): void;
  confirm(): void;
  back(): void;
  selectSku(value: InventorySkuOption): void;
  createSku(sku: string): void;
  clearSku(): void;
  checkCatalog(): void;
}

/** Общее создание из списка и прямой ссылки, с границей tenant/session. */
export function useCreateCatalogItem(
  direct: boolean = false,
  busy: () => boolean = () => false,
): CatalogCreation {
  const state = reactive(productCreationState());
  const open = ref(direct);
  const navigating = ref(false);
  const cache = useQueryClient();
  const preset = ref<ProductPreset | null>(null);
  const skuSelection = ref<CatalogSkuSelection | null>(null);
  const skuCode = ref<string | null>(null);
  const ctx = useCatalogContext(
    () => false,
    () => busy() || (state.pending && !navigating.value),
    () => {
      creation.cancel();
      preset.value = null;
      clearSku();
      open.value = direct;
    },
  );
  const skuSearch = useInventorySkuSearch(
    computed(
      () =>
        ctx.active.value &&
        open.value &&
        preset.value !== null &&
        preset.value !== "variable",
    ),
    ctx.sessionKey,
  );
  function clearSku(): void {
    skuSelection.value = null;
    skuCode.value = null;
    skuSearch.reset();
  }
  function selectSku(value: InventorySkuOption): void {
    skuSelection.value = { mode: "existing", inventoryItemId: value.id };
    skuCode.value = value.sku;
    skuSearch.reset();
  }
  function createSku(sku: string): void {
    skuSelection.value = { mode: "create", sku };
    skuCode.value = sku;
    skuSearch.reset();
  }
  const creation = new ProductCreation(
    state,
    (virtual, kind) =>
      catalogApi.createItem(
        virtual,
        kind,
        kind === "variable" ? null : skuSelection.value,
      ),
    async (id) => {
      const current = ctx.captureSession();
      await skuSearch.invalidate();
      if (!current()) return;
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
  function choose(value: ProductPreset): void {
    if (ctx.active.value && !state.pending && !state.uncertain) {
      preset.value = value;
      clearSku();
    }
  }
  function confirm(): void {
    const selected = state.createdId ? state.preset : preset.value;
    if (ctx.active.value && selected) void creation.create(selected);
  }
  function back(): void {
    if (state.pending || state.uncertain || state.createdId) return;
    creation.cancel();
    preset.value = null;
    clearSku();
  }
  function show(): void {
    creation.cancel();
    preset.value = null;
    clearSku();
    open.value = true;
  }
  function close(): void {
    if (state.pending) return;
    open.value = false;
    clearSku();
    preset.value = null;
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
  return {
    ctx,
    state,
    open,
    show,
    close,
    choose,
    confirm,
    back,
    preset,
    skuSearch,
    skuCode,
    skuId: computed(() =>
      skuSelection.value?.mode === "existing"
        ? skuSelection.value.inventoryItemId
        : null,
    ),
    selectSku,
    createSku,
    clearSku,
    checkCatalog,
  };
}
