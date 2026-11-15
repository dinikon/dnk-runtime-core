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
  InternalMoveAllocation,
  InternalMoveDestination,
  InternalMoveDestinationParams,
} from "./internal-move-posting.types";
import { useInternalMoveDestinations } from "./use-internal-move-posting-queries";
interface InternalMoveDestinationPicker {
  row: Ref<InternalMoveAllocation | null>;
  search: Ref<string>;
  offset: Ref<number>;
  items: ComputedRef<InternalMoveDestination[]>;
  total: ComputedRef<number>;
  loading: ComputedRef<boolean>;
  error: ComputedRef<string>;
  open: (row: InternalMoveAllocation) => void;
  close: () => void;
  setSearch: (search: string) => void;
  page: (offset: number) => void;
  retry: () => void;
}
export function useInternalMoveDestinationPicker(
  id: Ref<string>,
  scope: InventoryScopeState,
  identity: Ref<string>,
): InternalMoveDestinationPicker {
  const row = ref<InternalMoveAllocation | null>(null),
    search = ref(""),
    applied = ref(""),
    offset = ref(0);
  let timer: ReturnType<typeof setTimeout> | undefined;
  const params = computed<InternalMoveDestinationParams>(() => ({
    search: applied.value,
    offset: offset.value,
  }));
  const query = useInternalMoveDestinations(
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
  function open(value: InternalMoveAllocation): void {
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
