import { computed, type Ref, type ComputedRef } from "vue";
import {
  useInventoryItemQuery,
  useInventoryUomsQuery,
} from "./use-inventory-item-query";
import { usePackagingTypeQuery } from "./use-packaging-type-query";
import { usePackagingTypeSearch } from "./use-packaging-type-search";
import { InventorySettingsRequestError } from "./inventory-item-settings.errors";
import { PackagingTypeRequestError } from "./packaging-type.errors";
import type { PackagingTypePickerState } from "./item-packaging.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import type {
  InventoryItemDetails,
  InventoryUom,
} from "./inventory-item-settings.types";
export interface ItemPackagingFormContext {
  parent: ReturnType<typeof useInventoryItemQuery>;
  units: ReturnType<typeof useInventoryUomsQuery>;
  selected: ReturnType<typeof usePackagingTypeQuery>;
  search: ReturnType<typeof usePackagingTypeSearch>;
  currentParent: ComputedRef<InventoryItemDetails | undefined>;
  parentMissing: ComputedRef<boolean>;
  compatibleUoms: ComputedRef<InventoryUom[]>;
  ready: ComputedRef<boolean>;
  canSubmit: ComputedRef<boolean>;
  picker: ComputedRef<PackagingTypePickerState>;
  error: ComputedRef<string>;
  retry(): void;
  retrySelected(): void;
}
export function useItemPackagingFormContext(
  itemId: Ref<string>,
  typeId: Ref<string>,
  searchOpen: Ref<boolean>,
  identity: Ref<string>,
  scope: InventoryScopeState,
): ItemPackagingFormContext {
  const parent = useInventoryItemQuery(itemId, scope),
    units = useInventoryUomsQuery(scope),
    selected = usePackagingTypeQuery(typeId, scope);
  const search = usePackagingTypeSearch(searchOpen, scope, identity);
  const parentMissing = computed(
    () =>
      parent.error.value instanceof InventorySettingsRequestError &&
      [403, 404].includes(parent.error.value.status ?? 0),
  );
  const currentParent = computed(() =>
    scope.ready.value &&
    !parentMissing.value &&
    parent.data.value?.id === itemId.value
      ? parent.data.value
      : undefined,
  );
  const compatibleUoms = computed(() => {
    if (
      units.error.value instanceof InventorySettingsRequestError &&
      [403, 404].includes(units.error.value.status ?? 0)
    )
      return [];

    const dimension = units.data.value?.find(
      (unit) => unit.code === currentParent.value?.baseUom,
    )?.dimension;
    return dimension
      ? (units.data.value?.filter((unit) => unit.dimension === dimension) ?? [])
      : [];
  });
  const selectedType = computed(() =>
    selected.error.value instanceof PackagingTypeRequestError &&
    [403, 404].includes(selected.error.value.status ?? 0)
      ? undefined
      : selected.data.value?.id === typeId.value
        ? selected.data.value
        : undefined,
  );
  const ready = computed(
    () =>
      scope.ready.value &&
      !!currentParent.value &&
      !!compatibleUoms.value.length,
  );
  const canSubmit = computed(
    () =>
      ready.value &&
      !!selectedType.value?.isActive &&
      !selected.isFetching.value,
  );
  const picker = computed<PackagingTypePickerState>(() => ({
    search: search.search.value,
    options: search.options.value,
    total: search.total.value,
    loading: search.loading.value,
    fetchingMore: search.fetchingMore.value,
    hasMore: search.hasMore.value,
    error: search.error.value,
    selected: selectedType.value,
    selectedLoading: !!typeId.value && selected.isFetching.value,
    selectedError: selected.error.value?.message ?? "",
  }));
  const error = computed(
    () =>
      scope.error.value ||
      parent.error.value?.message ||
      units.error.value?.message ||
      "",
  );
  function retry(): void {
    if (scope.ready.value)
      void Promise.all([parent.refetch(), units.refetch()]);
  }
  function retrySelected(): void {
    if (scope.ready.value && typeId.value) void selected.refetch();
  }
  return {
    parent,
    units,
    selected,
    search,
    currentParent,
    parentMissing,
    compatibleUoms,
    ready,
    canSubmit,
    picker,
    error,
    retry,
    retrySelected,
  };
}
