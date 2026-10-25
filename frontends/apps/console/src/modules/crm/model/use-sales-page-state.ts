import {
  computed,
  ref,
  watch,
  onScopeDispose,
  type Ref,
  type ComputedRef,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import type { SalesKind } from "./sales.types";
import type { SalesFilters } from "./sales.types";
export function useSalesPageState(kind: () => SalesKind): {
  input: Ref<string>;
  view: ComputedRef<"kanban" | "list">;
  page: ComputedRef<number>;
  filters: ComputedRef<SalesFilters>;
  set: (values: Record<string, string | undefined>) => Promise<void>;
} {
  const route = useRoute(),
    router = useRouter();
  const input = ref(String(route.query.q ?? "")),
    search = ref(input.value);
  let timer: ReturnType<typeof setTimeout> | undefined;
  watch(input, (v) => {
    clearTimeout(timer);
    if (v === String(route.query.q ?? "")) {
      search.value = v;
      return;
    }
    timer = setTimeout(() => {
      search.value = v;
      void set({ q: v || undefined, page: undefined });
    }, 300);
  });
  watch(
    () => route.query.q,
    (v) => {
      input.value = String(v ?? "");
      search.value = input.value;
    },
  );
  onScopeDispose(() => clearTimeout(timer));
  const view = computed(() =>
    route.query.view === "list" ? "list" : "kanban",
  );
  const page = computed(() =>
    Math.max(1, parseInt(String(route.query.page ?? 1), 10) || 1),
  );
  const filters = computed<SalesFilters>(() => ({
    funnelId: String(route.query.funnel ?? ""),
    stageId: String(route.query.stage ?? ""),
    search: search.value,
    converted:
      kind() === "leads"
        ? route.query.converted === "all"
          ? undefined
          : route.query.converted === "yes"
        : undefined,
    offset: (page.value - 1) * 20,
    sort: route.query.sort === "title" ? "title" : "updated",
  }));
  async function set(values: Record<string, string | undefined>) {
    await router.replace({ query: { ...route.query, ...values } });
  }
  return { input, view, page, filters, set };
}
