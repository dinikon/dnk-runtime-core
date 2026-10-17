import { computed, reactive, ref, watch } from "vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { getApiErrorMessage, getApiErrorStatus } from "@/app/providers/http";
import { catalogApi } from "../api/catalog.api";
import { itemFromDto } from "../api/catalog.mapper";
import { loadAttributes, loadCategories, loadTags } from "./catalog-options";
import { useCatalogContext } from "./use-catalog-context";
import type { CatalogItem } from "./catalog.types";
import type {
  ProductEditorDraft,
  ProductSection,
  ProductStructure,
  ProductTab,
} from "./product.types";
import { productTabs } from "./product-presentation";

export function useProductPage(editing: boolean) {
  const draft = reactive<ProductEditorDraft>({ dirty: {}, resets: {} });
  const pending = ref(false),
    error = ref(""),
    conflict = ref(false),
    revision = ref(0),
    structureRequested = ref(false);
  const visited = ref<Record<string, CatalogItem>>({});
  const cache = useQueryClient();
  function clear() {
    pending.value = false;
    draft.dirty = {};
    draft.resets = {};
    visited.value = {};
    error.value = "";
    conflict.value = false;
    structureRequested.value = false;
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
    enabled: computed(
      () => enabled.value && item.data.value?.kind === "simple",
    ),
    queryFn: ({ signal }) => loadCategories(ctx.locale.value, signal),
  });
  const tags = useQuery({
    queryKey: computed(() => ctx.key("tag-options")),
    enabled: computed(
      () => enabled.value && item.data.value?.kind === "simple",
    ),
    queryFn: ({ signal }) => loadTags(ctx.locale.value, signal),
  });
  const schema = useQuery({
    queryKey: computed(() => ctx.key("product-schema")),
    enabled: computed(() => enabled.value && editing),
    queryFn: ({ signal }) => catalogApi.defaultSchema(ctx.locale.value, signal),
  });
  const offset = ref(0);
  const variants = useQuery({
    queryKey: computed(() => ctx.key("variant-page", id.value, offset.value)),
    enabled: computed(
      () => enabled.value && item.data.value?.kind === "variable",
    ),
    refetchOnWindowFocus: false,
    queryFn: async ({ signal }) => {
      const page = await catalogApi.listVariants(
        id.value,
        ctx.locale.value,
        offset.value,
        20,
        signal,
      );
      return { ...page, items: page.items.map(itemFromDto) };
    },
  });
  const variantId = computed(() =>
    typeof ctx.route.query.variant === "string" ? ctx.route.query.variant : "",
  );
  const variant = useQuery({
    queryKey: computed(() => ctx.key("selected-variant", variantId.value)),
    enabled: computed(
      () =>
        enabled.value &&
        !!variantId.value &&
        item.data.value?.kind === "variable",
    ),
    retry: false,
    refetchOnWindowFocus: false,
    queryFn: async ({ signal }) => {
      const child = itemFromDto(
        (await catalogApi.getItem(variantId.value, ctx.locale.value, signal))
          .item,
      );
      if (child.rootId !== id.value || child.kind !== "variant")
        throw new Error("Вариант не принадлежит этому товару.");
      return child;
    },
  });
  const allVariants = useQuery({
    queryKey: computed(() => ctx.key("structure-variants", id.value)),
    enabled: computed(
      () =>
        enabled.value &&
        item.data.value?.kind === "variable" &&
        structureRequested.value,
    ),
    refetchOnWindowFocus: false,
    queryFn: async ({ signal }) => {
      const result: CatalogItem[] = [];
      for (let offset = 0; ; offset += 100) {
        const page = await catalogApi.listVariants(
          id.value,
          ctx.locale.value,
          offset,
          100,
          signal,
        );
        result.push(...page.items.map(itemFromDto));
        if (result.length >= page.total) return result;
      }
    },
  });
  const structure = computed<ProductStructure | null>(() => {
    const root = item.data.value,
      children = allVariants.data.value;
    if (root?.kind !== "variable" || !children) return null;
    return {
      axes: root.own.axes,
      default_selection:
        root.own.default_selection?.values.map(([attribute_id, option_id]) => ({
          attribute_id,
          option_id,
        })) ?? null,
      variants: children.map((v) => ({
        item_id: v.id,
        selection: v.own.selection.values.map(([attribute_id, option_id]) => ({
          attribute_id,
          option_id,
        })),
      })),
    };
  });
  const tab = computed<ProductTab>(() => {
    const raw = ctx.route.query.tab;
    const valid = productTabs.some((v) => v.id === raw);
    if (!valid)
      return item.data.value?.kind === "variable" ? "inventory" : "general";
    if (raw === "general" && item.data.value?.kind === "variable")
      return "inventory";
    if (raw === "variants" && item.data.value?.kind !== "variable")
      return "general";
    return raw as ProductTab;
  });
  function selectTab(value: string) {
    void ctx.router.replace({ query: { ...ctx.route.query, tab: value } });
  }
  function selectVariant(value: string) {
    void ctx.router.replace({
      query: {
        ...ctx.route.query,
        variant: value || undefined,
        ...(editing ? { tab: "variants" } : {}),
      },
    });
  }
  watch(
    () => variant.data.value,
    (v) => {
      if (v && v.rootId === id.value)
        visited.value = { ...visited.value, [v.id]: v };
    },
    { immediate: true, flush: "post" },
  );
  watch(
    () => item.data.value,
    (v) => {
      if (v && !Object.values(draft.dirty).some(Boolean))
        revision.value = v.rootRevision;
    },
    { immediate: true },
  );
  watch(
    () => [id.value, ctx.locale.value],
    () => {
      clear();
      offset.value = 0;
      revision.value = item.data.value?.rootRevision ?? 0;
    },
  );
  const key = (itemId: string, section: ProductSection) =>
    `${itemId}:${section}:${["content", "galleries"].includes(section) ? ctx.locale.value : ""}`;
  const isDirty = (itemId: string, section: ProductSection) =>
    !!draft.dirty[key(itemId, section)];
  const resetFor = (itemId: string, section: ProductSection) =>
    draft.resets[key(itemId, section)] ?? 0;
  const mark = (itemId: string, section: ProductSection, value: boolean) => {
    draft.dirty[key(itemId, section)] = value;
  };
  const blocked = computed(
    () => pending.value || conflict.value || !ctx.active.value,
  );
  async function mutate(
    itemId: string,
    section: ProductSection,
    action: () => Promise<{ root_revision: number } | void>,
  ) {
    if (
      blocked.value ||
      (itemId !== id.value && isDirty(id.value, "structure"))
    )
      return;
    pending.value = true;
    error.value = "";
    const current = ctx.captureSession();
    try {
      const result = await action();
      if (!current()) return;
      if (result) revision.value = result.root_revision;
      mark(itemId, section, false);
      await cache.invalidateQueries({
        queryKey: ["catalog", ctx.tenantId.value],
        refetchType: "none",
      });
      const fresh = await item.refetch();
      revision.value = fresh.data?.rootRevision ?? revision.value;
      if (itemId !== id.value) {
        const child = itemFromDto(
          (await catalogApi.getItem(itemId, ctx.locale.value)).item,
        );
        visited.value = { ...visited.value, [itemId]: child };
        cache.setQueryData(ctx.key("selected-variant", itemId), child);
      }
      if (
        itemId === id.value &&
        section !== "kind" &&
        section !== "structure"
      ) {
        for (const childId of Object.keys(visited.value)) {
          visited.value[childId] = itemFromDto(
            (await catalogApi.getItem(childId, ctx.locale.value)).item,
          );
        }
      }
      const k = key(itemId, section);
      draft.resets[k] = (draft.resets[k] ?? 0) + 1;
      if (item.data.value?.kind === "variable") await variants.refetch();
      if (
        (section === "structure" || section === "kind") &&
        item.data.value?.kind === "variable"
      ) {
        await allVariants.refetch();
        const ids = new Set(allVariants.data.value?.map((v) => v.id));
        visited.value = Object.fromEntries(
          Object.entries(visited.value).filter(([id]) => ids.has(id)),
        );
        if (variantId.value && !ids.has(variantId.value)) selectVariant("");
      }
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
  const save = (
    itemId: string,
    section: ProductSection,
    value: Record<string, unknown>,
  ) =>
    mutate(itemId, section, () =>
      catalogApi.saveItem(
        itemId,
        section,
        revision.value,
        value,
        ctx.locale.value,
      ),
    );
  const inherit = (itemId: string, section: "content" | "galleries") =>
    mutate(itemId, section, () =>
      catalogApi.inheritSection(
        itemId,
        section,
        ctx.locale.value,
        revision.value,
      ),
    );
  const upload = (itemId: string, file: File, main: boolean) =>
    mutate(itemId, "galleries", () =>
      catalogApi.uploadImage(
        itemId,
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
    const keys = Object.keys(draft.dirty);
    draft.dirty = {};
    const fresh = await item.refetch();
    revision.value = fresh.data?.rootRevision ?? revision.value;
    for (const childId of Object.keys(visited.value)) {
      try {
        visited.value[childId] = itemFromDto(
          (await catalogApi.getItem(childId, ctx.locale.value)).item,
        );
      } catch {
        delete visited.value[childId];
      }
    }
    for (const k of keys) draft.resets[k] = (draft.resets[k] ?? 0) + 1;
    if (item.data.value?.kind === "variable") {
      await variants.refetch();
      if (structureRequested.value) await allVariants.refetch();
    }
    if (schema.isError.value) await schema.refetch();
    if (attributes.isError.value) await attributes.refetch();
    if (categories.isError.value) await categories.refetch();
    if (tags.isError.value) await tags.refetch();
    error.value = "";
    conflict.value = false;
  }
  async function replaceStructure(value: ProductStructure) {
    const ids = new Set(value.variants.map((v) => v.item_id));
    const removed =
      allVariants.data.value?.filter((v) => !ids.has(v.id)).map((v) => v.id) ??
      [];
    if (
      removed.length &&
      !window.confirm(
        `Будут удалены ${removed.length} вариантов и их данные. Продолжить?`,
      )
    )
      return;
    await save(id.value, "structure", {
      structure: value,
      removed_ids: removed,
    });
  }
  const imageUrl = (itemId: string, imageId: string) =>
    catalogApi.imageUrl(itemId, ctx.locale.value, imageId);
  return {
    ctx,
    id,
    item,
    attributes,
    categories,
    tags,
    schema,
    variants,
    offset,
    variant,
    variantId,
    visited,
    allVariants,
    structure,
    structureRequested,
    tab,
    selectTab,
    selectVariant,
    draft,
    pending,
    error,
    conflict,
    blocked,
    isDirty,
    resetFor,
    mark,
    save,
    inherit,
    upload,
    reload,
    replaceStructure,
    imageUrl,
  };
}
