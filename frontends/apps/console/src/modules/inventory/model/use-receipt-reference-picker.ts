import {
  computed,
  ref,
  watch,
  onScopeDispose,
  type Ref,
  type ComputedRef,
} from "vue";
import type { InventoryScopeState } from "./use-inventory-scope";
import type {
  IntakeRow,
  ReceiptReferenceKind,
  ReceiptReferencesParams,
  IntakeReference,
} from "./receipt-posting.types";
import { useReceiptReferenceQuery } from "./use-receipt-posting-queries";
export interface ReceiptPickerSelection {
  key: string;
  kind: ReceiptReferenceKind;
  documentLineId: string;
  lotId: string;
}
export interface ReceiptReferencePickerState {
  selection: Ref<ReceiptPickerSelection | null>;
  search: Ref<string>;
  offset: Ref<number>;
  items: ComputedRef<IntakeReference[]>;
  total: ComputedRef<number>;
  loading: ComputedRef<boolean>;
  error: ComputedRef<string>;
  open(row: IntakeRow, kind: ReceiptReferenceKind): void;
  close(): void;
  setSearch(value: string): void;
  page(value: number): void;
  retry(): void;
}
export function useReceiptReferencePicker(
  id: Ref<string>,
  scope: InventoryScopeState,
  identity: Ref<string>,
): ReceiptReferencePickerState {
  const selection = ref<ReceiptPickerSelection | null>(null),
    search = ref(""),
    committed = ref(""),
    offset = ref(0);
  let timer: ReturnType<typeof setTimeout> | undefined;
  const params = computed<ReceiptReferencesParams>(() => ({
    kind: selection.value?.kind ?? "locations",
    documentLineId:
      selection.value?.kind !== "locations"
        ? selection.value?.documentLineId
        : undefined,
    lotId:
      selection.value?.kind === "serials"
        ? selection.value.lotId || undefined
        : undefined,
    search: committed.value,
    offset: offset.value,
    limit: 20,
  }));
  const query = useReceiptReferenceQuery(
    id,
    params,
    computed(() => selection.value !== null),
    scope,
  );
  function close(): void {
    selection.value = null;
    clearTimeout(timer);
    search.value = "";
    committed.value = "";
    offset.value = 0;
  }
  watch(identity, close, { flush: "sync" });
  onScopeDispose(() => clearTimeout(timer));
  return {
    selection,
    search,
    offset,
    items: computed(() => query.data.value?.items ?? []),
    total: computed(() => query.data.value?.total ?? 0),
    loading: computed(
      () => query.isFetching.value || search.value.trim() !== committed.value,
    ),
    error: computed(() => query.error.value?.message ?? ""),
    open: (row, kind) => {
      close();
      selection.value = {
        key: row.key,
        kind,
        documentLineId: row.documentLineId,
        lotId: row.lotId,
      };
    },
    close,
    setSearch: (value) => {
      search.value = value;
      clearTimeout(timer);
      timer = setTimeout(() => {
        committed.value = value.trim();
        offset.value = 0;
      }, 250);
    },
    page: (value) => (offset.value = value),
    retry: () => {
      void query.refetch();
    },
  };
}
