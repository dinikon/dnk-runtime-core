import {
  computed,
  onBeforeUnmount,
  ref,
  watch,
  type Ref,
  type ComputedRef,
} from "vue";
import { onBeforeRouteLeave, onBeforeRouteUpdate } from "vue-router";
import { getApiErrorMessage } from "@/app/providers/http";
import type { CatalogListItem } from "./catalog.types";
import type { ProductPatch } from "./product.types";
import type {
  CatalogQuickEditSection,
  CatalogQuickEditSelection,
  CatalogQuickEditTarget,
} from "./catalog-table.types";
import { clone } from "./clone";
import { useCatalogQuickEditQuery } from "./catalog-quick-edit.queries";
import { useUpdateCatalogCell } from "./use-update-catalog-cell";

interface CatalogQuickEditing {
  selection: Ref<CatalogQuickEditSelection | null>;
  draftSource: Ref<CatalogQuickEditTarget | null>;
  dirty: Ref<boolean>;
  query: ReturnType<typeof useCatalogQuickEditQuery>;
  mutation: ReturnType<typeof useUpdateCatalogCell>;
  key: ComputedRef<string>;
  error: ComputedRef<string>;
  open(item: CatalogListItem, section: CatalogQuickEditSection): void;
  close(): void;
  save(patch: ProductPatch): Promise<void>;
}

export function useCatalogQuickEdit(
  tenant: Ref<string>,
  session: Ref<string>,
  locale: Ref<string>,
  active: Ref<boolean>,
): CatalogQuickEditing {
  const selection = ref<CatalogQuickEditSelection | null>(null),
    dirty = ref(false);
  const query = useCatalogQuickEditQuery(selection, tenant, session, locale);
  const mutation = useUpdateCatalogCell(session);
  const draftSource = ref<CatalogQuickEditTarget | null>(null);
  watch([query.data, query.isFetching], ([value, fetching]) => {
    // Once editing begins, a refetch cannot change the form's stock owner.
    if (
      selection.value &&
      value &&
      !fetching &&
      !dirty.value &&
      !query.isError.value
    )
      draftSource.value = clone(value);
  });
  let mounted = true;
  const key = computed(() =>
    JSON.stringify([session.value, locale.value, selection.value]),
  );
  const error = computed(() => {
    const cause = mutation.error.value ?? query.error.value;
    return cause
      ? getApiErrorMessage(
          cause,
          "Не удалось сохранить изменения. Ваш ввод сохранён.",
        )
      : "";
  });
  function clear(): void {
    selection.value = null;
    draftSource.value = null;
    dirty.value = false;
    mutation.reset();
  }
  watch([session, locale], clear, { flush: "sync" });
  function open(item: CatalogListItem, section: CatalogQuickEditSection): void {
    if (
      !active.value ||
      mutation.isPending.value ||
      (section === "price" && item.kind === "variable")
    )
      return;
    mutation.reset();
    dirty.value = false;
    draftSource.value = null;
    selection.value = {
      id: item.id,
      rootId: item.kind === "variant" ? (item.parent_id ?? null) : null,
      section,
    };
  }
  function close(): void {
    if (!mutation.isPending.value) clear();
  }
  function canLeave(): boolean {
    if (mutation.isPending.value) return false;
    if (
      dirty.value &&
      !window.confirm("Есть несохранённые изменения. Отказаться от них?")
    )
      return false;
    clear();
    return true;
  }
  onBeforeRouteLeave(canLeave);
  onBeforeRouteUpdate(
    (to, from) => to.fullPath === from.fullPath || canLeave(),
  );
  const unload = (event: BeforeUnloadEvent): void => {
    if (dirty.value || mutation.isPending.value) {
      event.preventDefault();
      event.returnValue = "";
    }
  };
  window.addEventListener("beforeunload", unload);
  onBeforeUnmount(() => {
    mounted = false;
    window.removeEventListener("beforeunload", unload);
  });
  async function save(patch: ProductPatch): Promise<void> {
    const target = draftSource.value;
    if (
      !target ||
      !selection.value ||
      !active.value ||
      query.isFetching.value ||
      query.isError.value ||
      mutation.isPending.value
    )
      return;
    const captured = key.value;
    try {
      await mutation.mutateAsync({
        id: target.item.id,
        rootId: target.rootId,
        tenant: tenant.value,
        session: session.value,
        locale: locale.value,
        patch,
      });
      if (mounted && key.value === captured) clear();
    } catch {
      /* Mutation error is shown beside the preserved draft. */
    }
  }
  return {
    selection,
    draftSource,
    dirty,
    query,
    mutation,
    key,
    error,
    open,
    close,
    save,
  };
}
