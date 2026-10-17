import { computed, reactive, ref, watch } from "vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { getApiErrorMessage, getApiErrorStatus } from "@/app/providers/http";
import { catalogApi } from "../api/catalog.api";
import { itemFromDto } from "../api/catalog.mapper";
import { loadAttributes, loadCategories, loadTags } from "./catalog-options";
import { useCatalogContext } from "./use-catalog-context";
import type {
  ProductEditorDraft,
  ProductSection,
  ProductTab,
} from "./product.types";
import { productTabs } from "./product-presentation";

export function useProductPage(editing: boolean) {
  const draft = reactive<ProductEditorDraft>({ dirty: {}, resets: {} });
  const pending = ref(false),
    error = ref(""),
    conflict = ref(false),
    revision = ref(0);
  const cache = useQueryClient();
  function clear() {
    pending.value = false;
    draft.dirty = {};
    draft.resets = {};
    error.value = "";
    conflict.value = false;
    revision.value = 0;
  }
  const ctx = useCatalogContext(
    () => Object.values(draft.dirty).some(Boolean),
    () => pending.value,
    clear,
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
  watch(
    () => item.data.value,
    (value) => {
      if (value && !Object.values(draft.dirty).some(Boolean))
        revision.value = value.revision;
    },
    { immediate: true },
  );
  watch(
    () => [id.value, ctx.locale.value],
    () => {
      clear();
      revision.value = item.data.value?.revision ?? 0;
    },
  );
  const key = (section: ProductSection) =>
    `${section}:${["content", "galleries"].includes(section) ? ctx.locale.value : ""}`;
  const isDirty = (section: ProductSection) => !!draft.dirty[key(section)];
  const resetFor = (section: ProductSection) => draft.resets[key(section)] ?? 0;
  const mark = (section: ProductSection, value: boolean) => {
    draft.dirty[key(section)] = value;
  };
  const blocked = computed(
    () => pending.value || conflict.value || !ctx.active.value,
  );
  async function mutate(
    section: ProductSection,
    action: () => Promise<{ revision: number } | void>,
  ) {
    if (blocked.value) return;
    pending.value = true;
    error.value = "";
    const current = ctx.captureSession();
    try {
      const result = await action();
      if (!current()) return;
      if (result) revision.value = result.revision;
      mark(section, false);
      await cache.invalidateQueries({
        queryKey: ["catalog", ctx.tenantId.value],
        refetchType: "none",
      });
      const fresh = await item.refetch();
      if (!current()) return;
      revision.value = fresh.data?.revision ?? revision.value;
      const sectionKey = key(section);
      draft.resets[sectionKey] = (draft.resets[sectionKey] ?? 0) + 1;
    } catch (e) {
      if (current()) {
        error.value = getApiErrorMessage(
          e,
          "Не удалось сохранить раздел. Ввод сохранён.",
        );
        conflict.value = getApiErrorStatus(e) === 409;
      }
    } finally {
      if (current()) pending.value = false;
    }
  }
  const save = (section: ProductSection, value: Record<string, unknown>) =>
    mutate(section, () =>
      catalogApi.saveItem(
        id.value,
        section,
        revision.value,
        value,
        ctx.locale.value,
      ),
    );
  const remove = (section: "content" | "galleries") =>
    mutate(section, () =>
      catalogApi.deleteSection(
        id.value,
        section,
        ctx.locale.value,
        revision.value,
      ),
    );
  const upload = (file: File, main: boolean) =>
    mutate("galleries", () =>
      catalogApi.uploadImage(
        id.value,
        ctx.locale.value,
        revision.value,
        file,
        main,
      ),
    );
  async function reload() {
    if (
      Object.values(draft.dirty).some(Boolean) &&
      !window.confirm(
        "Отказаться от всех несохранённых изменений и загрузить актуальную карточку?",
      )
    )
      return;
    const fresh = await item.refetch();
    if (fresh.isError) return;
    for (const sectionKey of Object.keys(draft.dirty))
      draft.resets[sectionKey] = (draft.resets[sectionKey] ?? 0) + 1;
    draft.dirty = {};
    revision.value = fresh.data?.revision ?? revision.value;
    if (schema.isError.value) await schema.refetch();
    if (attributes.isError.value) await attributes.refetch();
    if (categories.isError.value) await categories.refetch();
    if (tags.isError.value) await tags.refetch();
    error.value = "";
    conflict.value = false;
  }
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
    conflict,
    blocked,
    isDirty,
    resetFor,
    mark,
    save,
    remove,
    upload,
    reload,
    imageUrl,
  };
}
