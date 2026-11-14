import {
  computed,
  ref,
  watch,
  onBeforeUnmount,
  type Ref,
  type ComputedRef,
} from "vue";
import {
  useCounterpartyReferencesQuery,
  type CounterpartyReferencesParams,
  type CounterpartyReference,
} from "@/modules/crm";
import type { SupplierModelKey } from "./supplier-source.types";
import type { SupplierScopeState } from "./use-supplier-scope";
export interface SupplierLookup {
  search: Ref<string>;
  params: Ref<CounterpartyReferencesParams>;
  selected: Ref<CounterpartyReference | null>;
  items: ComputedRef<CounterpartyReference[]>;
  total: ComputedRef<number>;
  loading: ComputedRef<boolean>;
  error: ComputedRef<string>;
  setSearch(value: string): void;
  page(offset: number): void;
  select(value: CounterpartyReference): void;
  reset(): void;
  retry(): void;
}
export function useSupplierLookup(
  scope: SupplierScopeState,
  enabled: Ref<boolean>,
  modelKey: Ref<SupplierModelKey>,
): SupplierLookup {
  const search = ref(""),
    params = ref<CounterpartyReferencesParams>({
      model_key: modelKey.value,
      search: "",
      offset: 0,
      limit: 20,
    }),
    selected = ref<CounterpartyReference | null>(null);
  const query = useCounterpartyReferencesQuery(
    params,
    scope.key,
    computed(() => scope.ready.value && enabled.value),
  );
  let timer: ReturnType<typeof setTimeout> | undefined;
  function reset(): void {
    clearTimeout(timer);
    search.value = "";
    params.value = {
      model_key: modelKey.value,
      search: "",
      offset: 0,
      limit: 20,
    };
    selected.value = null;
  }
  watch(scope.key, reset, { flush: "sync" });
  watch(modelKey, reset, { flush: "sync" });
  onBeforeUnmount(() => clearTimeout(timer));
  return {
    search,
    params,
    selected,
    items: computed(() => query.data.value?.items ?? []),
    total: computed(() => query.data.value?.total ?? 0),
    loading: computed(() => query.isFetching.value),
    error: computed(() => query.error.value?.message ?? ""),
    setSearch: (value) => {
      search.value = value;
      clearTimeout(timer);
      timer = setTimeout(() => {
        params.value = { ...params.value, search: value.trim(), offset: 0 };
      }, 250);
    },
    page: (offset) => {
      params.value = { ...params.value, offset };
    },
    select: (value) => {
      selected.value = value;
    },
    reset,
    retry: () => {
      void query.refetch();
    },
  };
}
