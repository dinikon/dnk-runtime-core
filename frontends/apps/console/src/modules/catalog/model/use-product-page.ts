import {
  useInventorySkuSearch,
  type InventorySkuSearch,
} from "@/modules/inventory";
import { useSetCatalogSku } from "./use-set-catalog-sku";
import type { CatalogSkuSelection } from "./catalog-sku.types";
import {
  computed,
  reactive,
  ref,
  watch,
  onBeforeUnmount,
  type Ref,
  type ComputedRef,
} from "vue";
import {
  useQuery,
  useQueryClient,
  type UseQueryReturnType,
} from "@tanstack/vue-query";
import { getApiErrorMessage } from "@/app/providers/http";
import { catalogApi } from "../api/catalog.api";
import { useCatalogContext } from "./use-catalog-context";
import type { ProductSection } from "./product.types";
import axios from "axios";
import type { ProductPatch } from "./product.types";
import { ProductAutosave, type AutosaveState } from "./product-autosave";
import { sectionError, fieldSections } from "./product-validation";
import { useProductContentDraft } from "./use-product-content-draft";

interface ProductPageState {
  ctx: ReturnType<typeof useCatalogContext>;
  id: ComputedRef<string>;
  scope: ComputedRef<string>;
  item: UseQueryReturnType<import("./catalog.types").CatalogItem, Error>;
  schema: UseQueryReturnType<import("./catalog.types").CatalogSchema, Error>;
  skuSearch: InventorySkuSearch;
  skuMutation: ReturnType<typeof useSetCatalogSku>;
  setSku(selection: CatalogSkuSelection): Promise<void>;
  pending: ComputedRef<boolean>;
  error: ComputedRef<string>;
  blocked: ComputedRef<boolean>;
  uploading: Ref<boolean>;
  resets: Partial<Record<ProductSection, number>>;
  contentValues: ComputedRef<Record<string, string>>;
  contentOverrides: ReturnType<typeof useProductContentDraft>["values"];
  changeContent: ReturnType<typeof useProductContentDraft>["change"];
  isDirty(section: ProductSection): boolean;
  resetFor(section: ProductSection): number;
  fieldError(section: ProductSection): string;
  save(section: ProductSection, value: Record<string, unknown>): void;
  upload(file: File, main: boolean): Promise<void>;
  reload(): Promise<void>;
  retry(): Promise<void>;
  flush(): Promise<boolean>;
  imageUrl(imageId: string): string;
  saveStatus: ComputedRef<string>;
}

export function useProductPage(variantId?: Ref<string>): ProductPageState {
  const state = reactive<AutosaveState>({
    entries: {},
    pending: false,
    paused: false,
    error: "",
    held: false,
  });
  const resets = reactive<Partial<Record<ProductSection, number>>>({});
  const uploading = ref(false);
  const reloading = ref(false);
  let uploadWork: Promise<void> | null = null;
  const cache = useQueryClient();
  function clear() {
    autosave?.cancel();
    uploading.value = false;
    reloading.value = false;
    uploadWork = null;
    skuSearch.reset();
    skuMutation.reset();
  }
  const ctx = useCatalogContext(
    () => Object.keys(state.entries).length > 0 || state.paused,
    () =>
      state.pending ||
      uploading.value ||
      reloading.value ||
      skuMutation.isPending.value,
    clear,
    async () => {
      await autosave.flush();
      if (uploadWork) await uploadWork;
      return (
        !Object.keys(state.entries).length &&
        !uploading.value &&
        !state.paused &&
        !skuMutation.isPending.value
      );
    },
  );
  const id = computed(() => String(ctx.route.params.itemId));
  const enabled = computed(() => ctx.ready.value && !!ctx.locale.value);
  const item = useQuery({
    queryKey: computed(() =>
      ctx.key("get-item", id.value, variantId?.value ?? ""),
    ),
    enabled,
    refetchOnWindowFocus: false,
    queryFn: ({ queryKey, signal }) => {
      const rootId = String(queryKey[4]),
        childId = String(queryKey[5]),
        locale = String(queryKey[6]);
      return childId
        ? catalogApi.getVariant(rootId, childId, locale, signal)
        : catalogApi.getItem(rootId, locale, signal);
    },
  });
  const schema = useQuery({
    queryKey: computed(() => ctx.key("product-schema")),
    enabled,
    queryFn: ({ queryKey, signal }) =>
      catalogApi.defaultSchema(String(queryKey[4]), signal),
  });
  const skuScope = computed(
    () =>
      `${ctx.sessionKey.value}:${id.value}:${variantId?.value ?? ""}:${ctx.locale.value}`,
  );
  const skuSearch = useInventorySkuSearch(
    computed(() => enabled.value && item.data.value?.kind !== "variable"),
    skuScope,
  );
  const skuMutation = useSetCatalogSku(
    ctx.tenantId,
    ctx.sessionKey,
    skuSearch.invalidate,
  );
  watch(skuScope, () => skuMutation.reset(), { flush: "sync" });
  const isDirty = (section: ProductSection) => !!state.entries[section];
  const resetFor = (section: ProductSection) => resets[section] ?? 0;
  const fieldError = (section: ProductSection): string =>
    section === "sku" && skuMutation.error.value
      ? getApiErrorMessage(
          skuMutation.error.value,
          "Не удалось сохранить SKU. Повторите выбор.",
        )
      : (state.entries[section]?.error ?? "");
  const pending = computed(
    () =>
      state.pending ||
      uploading.value ||
      reloading.value ||
      skuMutation.isPending.value,
  );
  const error = computed(() => state.error);
  const blocked = computed(
    () => !ctx.active.value || !item.data.value || reloading.value,
  );
  const saveStatus = computed(() =>
    reloading.value
      ? "Обновление…"
      : state.paused
        ? "Не удалось сохранить"
        : pending.value
          ? "Сохранение…"
          : Object.values(state.entries).some((entry) => !!entry?.error)
            ? "Проверьте поля"
            : Object.keys(state.entries).length
              ? "Есть изменения"
              : "Все изменения сохранены",
  );
  const autosave = new ProductAutosave(
    state,
    async (value) => {
      if (!ctx.active.value)
        throw new Error("Запись в неактивную locale запрещена.");
      return variantId?.value
        ? catalogApi.updateVariant(
            id.value,
            variantId.value,
            value,
            ctx.locale.value,
          )
        : catalogApi.updateItem(id.value, value, ctx.locale.value);
    },
    async (sections) => {
      const current = ctx.captureSession();
      const targetId = id.value,
        targetLocale = ctx.locale.value;
      await cache.invalidateQueries({
        queryKey: ["catalog", ctx.tenantId.value],
        refetchType: variantId?.value ? "active" : "none",
      });
      if (!variantId?.value) await item.refetch();
      if (
        !current() ||
        id.value !== targetId ||
        ctx.locale.value !== targetLocale
      )
        return;
      for (const section of sections)
        if (!isDirty(section)) resets[section] = (resets[section] ?? 0) + 1;
    },
    (cause) => {
      const fields: Partial<Record<ProductSection, string>> = {};
      const detail = axios.isAxiosError(cause)
        ? cause.response?.data?.detail
        : undefined;
      const errors = Array.isArray(detail) ? detail : (detail?.errors ?? []);
      for (const issue of errors) {
        const field = issue.field ?? issue.loc?.[1];
        const section = fieldSections[String(field)];
        if (section)
          fields[section] = issue.message ?? issue.msg ?? "Проверьте значение.";
      }
      return {
        fields,
        message: getApiErrorMessage(
          cause,
          "Не удалось сохранить изменения. Ввод сохранён.",
        ),
      };
    },
  );
  const scope = computed(
    () =>
      `${ctx.sessionKey.value}:${id.value}:${variantId?.value ?? ""}:${ctx.locale.value}`,
  );
  const contentDraft = useProductContentDraft(
    () => item.data.value?.content,
    () => scope.value,
    () => isDirty("content"),
    (values) =>
      save("content", {
        expected_schema_version: schema.data.value?.schema.schema_version ?? 0,
        values,
      }),
    () => resetFor("content"),
  );
  watch(() => [id.value, variantId?.value, ctx.locale.value], clear);
  onBeforeUnmount(clear);
  async function setSku(selection: CatalogSkuSelection): Promise<void> {
    if (blocked.value || skuMutation.isPending.value) return;
    const captured = skuScope.value;
    const current = ctx.captureSession();
    try {
      await skuMutation.mutateAsync({
        id: id.value,
        variantId: variantId?.value,
        tenant: ctx.tenantId.value,
        session: ctx.sessionKey.value,
        selection,
      });
      if (current() && captured === skuScope.value) skuSearch.reset();
    } catch {
      /* The explicit selection and search remain available beside the field error. */
    }
  }
  function save(section: ProductSection, value: Record<string, unknown>) {
    let patch: ProductPatch;
    if (section === "content")
      patch = {
        content: value as unknown as NonNullable<ProductPatch["content"]>,
      };
    else if (section === "price")
      patch = {
        price_specification: value.price as ProductPatch["price_specification"],
      };
    else patch = value as ProductPatch;
    autosave.stage(
      section,
      patch,
      sectionError(section, patch, !!variantId?.value),
    );
  }
  function upload(file: File, main: boolean): Promise<void> {
    if (uploadWork) return uploadWork;
    uploading.value = true;
    const current = ctx.captureSession();
    const targetId = id.value,
      targetLocale = ctx.locale.value;
    const relevant = () =>
      current() && targetId === id.value && targetLocale === ctx.locale.value;
    async function perform(): Promise<void> {
      try {
        await autosave.flush();
        if (!relevant()) return;
        if (isDirty("galleries") || state.paused) {
          state.error =
            "Сначала исправьте ошибки галереи или повторите сохранение.";
          return;
        }
        state.held = true;
        if (variantId?.value)
          await catalogApi.uploadVariantImage(
            targetId,
            variantId.value,
            targetLocale,
            file,
            main,
          );
        else await catalogApi.uploadImage(targetId, targetLocale, file, main);
        if (!relevant()) return;
        await item.refetch();
        if (relevant()) resets.galleries = (resets.galleries ?? 0) + 1;
      } catch (cause) {
        if (relevant()) {
          state.error = getApiErrorMessage(
            cause,
            "Загрузка не подтверждена. Обновите данные перед повторной загрузкой файла.",
          );
          state.paused = true;
        }
      } finally {
        if (relevant()) {
          uploading.value = false;
          autosave.resume();
        }
      }
    }
    const task = perform();
    uploadWork = task;
    void task.finally(() => {
      if (uploadWork === task) uploadWork = null;
    });
    return task;
  }
  async function reload() {
    if (pending.value) return;
    if (
      Object.keys(state.entries).length &&
      !window.confirm(
        "Отказаться от несохранённых изменений и загрузить актуальную карточку?",
      )
    )
      return;
    const current = ctx.captureSession();
    const targetScope = scope.value;
    const relevant = () => current() && scope.value === targetScope;
    reloading.value = true;
    state.held = true;
    try {
      const fresh = await item.refetch();
      if (!relevant()) return;
      if (fresh.isError) {
        state.paused = true;
        state.error = getApiErrorMessage(
          fresh.error,
          "Не удалось обновить данные. Ваш ввод сохранён в карточке.",
        );
        return;
      }
      // Поколения сбросов монотонны: повторный reload сбрасывает даже
      // структурно неизменившийся ответ, а не оставляет локальный черновик.
      autosave.cancel();
      for (const section of new Set(Object.values(fieldSections)))
        resets[section] = (resets[section] ?? 0) + 1;
      await Promise.all([...(schema.isError.value ? [schema.refetch()] : [])]);
    } finally {
      if (relevant()) {
        reloading.value = false;
        state.held = false;
      }
    }
  }
  const retry = async () => {
    // После неизвестного результата upload сверяем галерею, не повторяя POST.
    const fresh = await item.refetch();
    if (!fresh.isError) autosave.retry();
  };
  const imageUrl = (imageId: string): string =>
    variantId?.value
      ? catalogApi.variantImageUrl(
          id.value,
          variantId.value,
          ctx.locale.value,
          imageId,
        )
      : catalogApi.imageUrl(id.value, ctx.locale.value, imageId);
  return {
    ctx,
    id,
    skuSearch,
    skuMutation,
    setSku,
    item,
    schema,
    pending,
    error,
    blocked,
    isDirty,
    resetFor,
    save,
    upload,
    reload,
    imageUrl,
    fieldError,
    saveStatus,
    retry,
    uploading,
    resets,
    scope,
    contentValues: computed(() =>
      variantId?.value
        ? {
            ...item.data.value?.effective_content,
            ...contentDraft.values.value,
          }
        : contentDraft.values.value,
    ),
    contentOverrides: contentDraft.values,
    flush: async (): Promise<boolean> => {
      await autosave.flush();
      if (uploadWork) await uploadWork;
      return (
        !Object.keys(state.entries).length &&
        !uploading.value &&
        !state.paused &&
        !skuMutation.isPending.value
      );
    },
    changeContent: contentDraft.change,
  };
}
