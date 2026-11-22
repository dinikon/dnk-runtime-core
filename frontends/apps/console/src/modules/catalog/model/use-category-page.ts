import { computed, ref, watch } from "vue";
import { getApiErrorMessage } from "@/app/providers/http";
import { useCatalogContext } from "./use-catalog-context";
import { useCategoryTree } from "./use-category-tree";
import { useCategoryMutation } from "./use-category-mutation";
import type { CategoryOption, CategoryChange } from "./category.types";

export function useCategoryPage() {
  const editing = ref<string | null>(null),
    dirty = ref(false),
    saving = ref(false),
    error = ref("");
  function close() {
    editing.value = null;
    dirty.value = false;
    error.value = "";
  }
  const ctx = useCatalogContext(
    () => dirty.value,
    () => saving.value,
    close,
  );
  watch(ctx.locale, close);
  const tree = useCategoryTree(ctx),
    mutation = useCategoryMutation(ctx);
  const selected = computed(() =>
    tree.options.value.find((row) => row.id === editing.value),
  );
  function open(id: string | null) {
    if (
      saving.value ||
      (dirty.value && !window.confirm("Отказаться от несохранённых изменений?"))
    )
      return;
    close();
    editing.value = id;
  }
  async function save(change: CategoryChange) {
    if (saving.value) return;
    const current = ctx.captureSession(),
      locale = ctx.locale.value;
    error.value = "";
    saving.value = true;
    try {
      await mutation.mutateAsync(change);
      if (current() && ctx.locale.value === locale) close();
    } catch (reason) {
      if (current() && ctx.locale.value === locale)
        error.value = getApiErrorMessage(
          reason,
          "Не удалось сохранить изменение категории.",
        );
    } finally {
      saving.value = false;
    }
  }
  function remove(row: CategoryOption) {
    if (
      window.confirm(
        "Удалить категорию «" + (row.name ?? row.sourceName) + "»?",
      )
    )
      void save({ action: "delete", id: row.id });
  }
  return {
    ctx,
    ...tree,
    editing,
    selected,
    dirty,
    saving,
    error,
    open,
    save,
    remove,
  };
}
