import { computed, reactive, ref, watch, onBeforeUnmount } from "vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { getApiErrorMessage } from "@/app/providers/http";
import { catalogApi } from "../api/catalog.api";
import { itemFromDto } from "../api/catalog.mapper";
import { loadAttributes, loadCategories, loadTags } from "./catalog-options";
import { useCatalogContext } from "./use-catalog-context";
import type { ProductSection, ProductTab } from "./product.types";
import axios from "axios";
import type { UpdateItemRequest } from "../api/catalog.dto";
import { ProductAutosave, type AutosaveState } from "./product-autosave";
import { sectionError, fieldSections } from "./product-validation";
import { productTabs } from "./product-presentation";
import { useProductContentDraft } from "./use-product-content-draft";

export function useProductPage(editing: boolean) {
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
  }
  const ctx = useCatalogContext(
    () => Object.keys(state.entries).length > 0 || state.paused,
    () => state.pending || uploading.value || reloading.value,
    clear,
    async () => {
      await autosave.flush();
      if (uploadWork) await uploadWork;
      return (
        !Object.keys(state.entries).length && !uploading.value && !state.paused
      );
    },
  );
  const id = computed(() => String(ctx.route.params.itemId));
  const enabled = computed(() => !!ctx.locale.value && !!ctx.tenantId.value);
  const item = useQuery({
    queryKey: computed(() => ctx.key("get-item", id.value)),
    enabled,
    refetchOnWindowFocus: false,
    queryFn: async ({ signal }) =>
      itemFromDto(
        (await catalogApi.getItem(id.value, ctx.locale.value, signal)).item,
      ),
  });
  const attributes = useQuery({
    queryKey: computed(() => ctx.key("attribute-options")),
    enabled,
    queryFn: ({ signal }) => loadAttributes(ctx.locale.value, signal),
  });
  const categories = useQuery({
    queryKey: computed(() => ctx.key("category-options")),
    enabled,
    queryFn: ({ signal }) => loadCategories(ctx.locale.value, signal),
  });
  const tags = useQuery({
    queryKey: computed(() => ctx.key("tag-options")),
    enabled,
    queryFn: ({ signal }) => loadTags(ctx.locale.value, signal),
  });
  const schema = useQuery({
    queryKey: computed(() => ctx.key("product-schema")),
    enabled: computed(() => enabled.value && editing),
    queryFn: ({ signal }) => catalogApi.defaultSchema(ctx.locale.value, signal),
  });
  const tab = computed<ProductTab>(() =>
    productTabs.some((t) => t.id === ctx.route.query.tab)
      ? (ctx.route.query.tab as ProductTab)
      : "general",
  );
  function selectTab(value: string) {
    void ctx.router.replace({ query: { ...ctx.route.query, tab: value } });
  }
  const isDirty = (section: ProductSection) => !!state.entries[section];
  const resetFor = (section: ProductSection) => resets[section] ?? 0;
  const fieldError = (section: ProductSection) =>
    state.entries[section]?.error ?? "";
  const pending = computed(
    () => state.pending || uploading.value || reloading.value,
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
      return catalogApi.updateItem(id.value, value, ctx.locale.value);
    },
    async (sections) => {
      const current = ctx.captureSession();
      const targetId = id.value,
        targetLocale = ctx.locale.value;
      await cache.invalidateQueries({
        queryKey: ["catalog", ctx.tenantId.value],
        refetchType: "none",
      });
      await item.refetch();
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
    () => `${ctx.sessionKey.value}:${id.value}:${ctx.locale.value}`,
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
  watch(() => [id.value, ctx.locale.value], clear);
  onBeforeUnmount(clear);
  function save(section: ProductSection, value: Record<string, unknown>) {
    let patch: UpdateItemRequest;
    if (section === "content")
      patch = {
        content: value as unknown as NonNullable<UpdateItemRequest["content"]>,
      };
    else if (section === "price")
      patch = {
        price_specification:
          value.price as UpdateItemRequest["price_specification"],
      };
    else patch = value as UpdateItemRequest;
    autosave.stage(section, patch, sectionError(section, patch));
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
        await catalogApi.uploadImage(targetId, targetLocale, file, main);
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
      await Promise.all([
        ...(schema.isError.value ? [schema.refetch()] : []),
        ...(attributes.isError.value ? [attributes.refetch()] : []),
        ...(categories.isError.value ? [categories.refetch()] : []),
        ...(tags.isError.value ? [tags.refetch()] : []),
      ]);
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
  const imageUrl = (imageId: string) =>
    catalogApi.imageUrl(id.value, ctx.locale.value, imageId);
  return {
    ctx,
    id,
    item,
    attributes,
    categories,
    tags,
    schema,
    tab,
    selectTab,
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
    contentValues: contentDraft.values,
    changeContent: contentDraft.change,
  };
}
