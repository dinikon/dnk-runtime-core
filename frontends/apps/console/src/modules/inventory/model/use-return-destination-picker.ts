import {
  computed,
  ref,
  watch,
  onBeforeUnmount,
  type Ref,
  type ComputedRef,
} from "vue";
import type { InventoryScopeState } from "./use-inventory-scope";
import type {
  ReturnAllocation,
  ReturnDestination,
  ReturnDestinationParams,
} from "./return-posting.types";
import { useReturnDestinations } from "./use-return-posting-queries";
interface ReturnDestinationPicker {
  row: Ref<ReturnAllocation | null>;
  search: Ref<string>;
  offset: Ref<number>;
  items: ComputedRef<ReturnDestination[]>;
  total: ComputedRef<number>;
  loading: ComputedRef<boolean>;
  error: ComputedRef<string>;
  open: (row: ReturnAllocation) => void;
  close: () => void;
  setSearch: (search: string) => void;
  page: (offset: number) => void;
  retry: () => void;
}
export function useReturnDestinationPicker(
  id: Ref<string>,
  scope: InventoryScopeState,
  identity: Ref<string>,
): ReturnDestinationPicker {
  const row = ref<ReturnAllocation | null>(null),
    search = ref(""),
    applied = ref(""),
    offset = ref(0);
  let timer: ReturnType<typeof setTimeout> | undefined;
  const params = computed<ReturnDestinationParams>(() => ({
    search: applied.value,
    offset: offset.value,
  }));
  const query = useReturnDestinations(
    id,
    params,
    computed(() => !!row.value),
    scope,
  );
  function close(): void {
    clearTimeout(timer);
    row.value = null;
    search.value = "";
    applied.value = "";
    offset.value = 0;
  }
  function open(value: ReturnAllocation): void {
    close();
    row.value = { ...value };
  }
  function setSearch(value: string): void {
    search.value = value;
    clearTimeout(timer);
    timer = setTimeout(() => {
      applied.value = value;
      offset.value = 0;
    }, 250);
  }
  function page(value: number): void {
    offset.value = Math.max(0, value);
  }
  function retry(): void {
    void query.refetch();
  }
  watch(identity, close, { flush: "sync" });
  onBeforeUnmount(() => clearTimeout(timer));
  return {
    row,
    search,
    offset,
    items: computed(() =>
      scope.ready.value ? (query.data.value?.items ?? []) : [],
    ),
    total: computed(() => query.data.value?.total ?? 0),
    loading: computed(() => query.isFetching.value),
    error: computed(() => query.error.value?.message ?? ""),
    open,
    close,
    setSearch,
    page,
    retry,
  };
}
