import {
  computed,
  ref,
  watch,
  onScopeDispose,
  type Ref,
  type ComputedRef,
} from "vue";
import { useRoute, useRouter } from "vue-router";
export function useFunnelsPageState(): {
  search: Ref<string>;
  modelKey: ComputedRef<string>;
  offset: ComputedRef<number>;
  page: (n: number) => void;
  setType: (value: string) => void;
} {
  const route = useRoute(),
    router = useRouter(),
    search = ref(String(route.query.q ?? ""));
  let timer: ReturnType<typeof setTimeout> | undefined;
  watch(search, (value) => {
    clearTimeout(timer);
    if (value === String(route.query.q ?? "")) return;
    timer = setTimeout(
      () =>
        void router.replace({
          query: { ...route.query, q: value || undefined, page: undefined },
        }),
      300,
    );
  });
  watch(
    () => route.query.q,
    (value) => (search.value = String(value ?? "")),
  );
  onScopeDispose(() => clearTimeout(timer));
  const modelKey = computed(() => String(route.query.type ?? "")),
    offset = computed(
      () =>
        Math.max(0, (parseInt(String(route.query.page ?? 1), 10) - 1) * 100) ||
        0,
    );
  function page(n: number): void {
    void router.replace({ query: { ...route.query, page: String(n) } });
  }
  function setType(value: string): void {
    void router.replace({
      query: { ...route.query, type: value || undefined, page: undefined },
    });
  }
  return { search, modelKey, offset, page, setType };
}
