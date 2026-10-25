import { computed, type ComputedRef } from "vue";
import { useRoute, useRouter } from "vue-router";
interface ImportsPageState {
  route: ReturnType<typeof useRoute>;
  router: ReturnType<typeof useRouter>;
  id: ComputedRef<string>;
  open: ComputedRef<boolean>;
  page: ComputedRef<number>;
  rowPage: ComputedRef<number>;
  outcome: ComputedRef<string>;
  query: (values: Record<string, string | number | undefined>) => void;
  show: (importId?: string) => void;
  close: () => void;
}
export function useImportsPageState(): ImportsPageState {
  const route = useRoute(),
    router = useRouter();
  const id = computed(() =>
    typeof route.params.importId === "string" ? route.params.importId : "",
  );
  const open = computed(() => !!id.value || route.path.endsWith("/new"));
  const page = computed(() => Math.max(1, Number(route.query.page) || 1));
  const rowPage = computed(() =>
    Math.max(1, Number(route.query.row_page) || 1),
  );
  const outcome = computed(() =>
    ["errors", "warnings", "created", "updated", "skipped"].includes(
      String(route.query.result),
    )
      ? String(route.query.result)
      : "",
  );
  function query(values: Record<string, string | number | undefined>): void {
    void router.replace({ query: { ...route.query, ...values } });
  }
  function show(importId?: string): void {
    void router.push({
      path: `/catalog/imports/${importId || "new"}`,
      query: { locale: route.query.locale, page: route.query.page },
    });
  }
  function close(): void {
    void router.push({
      path: "/catalog/imports",
      query: { locale: route.query.locale, page: route.query.page },
    });
  }
  return {
    route,
    router,
    id,
    open,
    page,
    rowPage,
    outcome,
    query,
    show,
    close,
  };
}
