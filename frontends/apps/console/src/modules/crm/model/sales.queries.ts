import type { SourceContactPreview } from "./sales.types";
import { salesKeys } from "./sales.query-keys";
import type { UseQueryReturnType } from "@tanstack/vue-query";
import type { ComputedRef } from "vue";
import type { Contact, Company } from "./crm.types";
import type {
  SaleRecord,
  SalesPage,
  ConversionContext,
  CatalogChoice,
  SaleSummary,
} from "./sales.types";
import { useSalesScope } from "./sales.scope";
import { computed, type Ref } from "vue";
import { useQuery, useQueries } from "@tanstack/vue-query";
import { useContactPointLabels } from "@/modules/contact-points";
import { salesApi } from "../api/sales.api";
import {
  crmContactsApi,
  crmCompaniesApi,
  crmContactPointsApi,
} from "../api/crm.api";
import { searchSalesCatalog } from "@/modules/catalog";
import type { FunnelStage } from "@/modules/funnel";
interface SalesColumnQueryState {
  stage: FunnelStage;
  items: SaleSummary[];
  total: number | null;
  loading: boolean;
  fetching: boolean;
  error: Error | null;
}
import type { Funnel } from "@/modules/funnel";
import type { SalesKind, SalesFilters } from "./sales.types";
export function useSalesPeople(): {
  contacts: UseQueryReturnType<Contact[], Error>;
  companies: UseQueryReturnType<Company[], Error>;
} {
  const scope = useSalesScope();
  const contacts = useQuery({
    queryKey: computed(() => salesKeys.people(scope.value, "contacts")),
    queryFn: ({ signal }) => crmContactsApi.list(signal),
  });
  const companies = useQuery({
    queryKey: computed(() => salesKeys.people(scope.value, "companies")),
    queryFn: ({ signal }) => crmCompaniesApi.list(signal),
  });
  return { contacts, companies };
}
export function useSale(
  kind: Ref<SalesKind>,
  id: Ref<string>,
): UseQueryReturnType<SaleRecord, Error> {
  const scope = useSalesScope();
  return useQuery({
    queryKey: computed(() =>
      salesKeys.detail(scope.value, kind.value, id.value),
    ),
    queryFn: ({ signal }) => salesApi.get(kind.value, id.value, signal),
    enabled: computed(() => !!id.value),
  });
}
export function useSalesList(
  kind: Ref<SalesKind>,
  filters: Ref<SalesFilters>,
  enabled: Ref<boolean>,
): UseQueryReturnType<SalesPage, Error> {
  const scope = useSalesScope();
  return useQuery({
    queryKey: computed(() =>
      salesKeys.list(scope.value, kind.value, filters.value),
    ),
    queryFn: ({ signal }) => salesApi.list(kind.value, filters.value, signal),
    enabled,
  });
}
export function useSalesColumns(
  kind: Ref<SalesKind>,
  funnel: Ref<Funnel | undefined>,
  filters: Ref<SalesFilters>,
  offsets: Ref<Record<string, number>>,
  enabled: Ref<boolean>,
): {
  columns: ComputedRef<SalesColumnQueryState[]>;
  retry: (stageId: string) => Promise<void>;
} {
  const scope = useSalesScope();
  const definitions = computed(() =>
    (funnel.value?.stages ?? [])
      .filter((s) => !filters.value.stageId || s.id === filters.value.stageId)
      .flatMap((stage) =>
        Array.from(
          { length: Math.floor((offsets.value[stage.id] ?? 0) / 20) + 1 },
          (_, index) => ({
            stageId: stage.id,
            filters: {
              ...filters.value,
              stageId: stage.id,
              offset: index * 20,
            },
          }),
        ),
      ),
  );
  const queries = useQueries({
    queries: computed(() =>
      definitions.value.map((value) => {
        const request = { ...value.filters };
        const requestKind = kind.value;
        return {
          queryKey: salesKeys.column(scope.value, requestKind, request),
          queryFn: ({ signal }: { signal: AbortSignal }) =>
            salesApi.list(requestKind, request, signal),
          enabled: enabled.value,
        };
      }),
    ),
  });
  const columns = computed(() => {
    const winner = new Map<string, SaleSummary>();
    for (const page of queries.value)
      for (const item of page.data?.items ?? []) {
        const previous = winner.get(item.id);
        if (!previous || previous.positionRevision < item.positionRevision)
          winner.set(item.id, item);
      }
    return (funnel.value?.stages ?? [])
      .filter((s) => !filters.value.stageId || s.id === filters.value.stageId)
      .map((stage) => {
        const pages = queries.value.filter(
          (_, i) => definitions.value[i]?.stageId === stage.id,
        );
        const items = pages
          .flatMap((q) => q.data?.items ?? [])
          .filter((item) => winner.get(item.id)?.stageId === stage.id);
        return {
          stage,
          items: [...new Map(items.map((i) => [i.id, i])).values()],
          total: pages[0]?.data?.total ?? null,
          loading: !!pages[0]?.isPending,
          fetching: pages.some((q) => q.isFetching),
          error: pages.find((q) => q.error)?.error ?? null,
        };
      });
  });
  async function retry(stageId: string): Promise<void> {
    await Promise.all(
      queries.value
        .filter((_, i) => definitions.value[i]?.stageId === stageId)
        .map((q) => q.refetch()),
    );
  }
  return { columns, retry };
}
export function useConversionContext(
  id: Ref<string>,
  enabled: Ref<boolean>,
): UseQueryReturnType<ConversionContext, Error> {
  const scope = useSalesScope();
  return useQuery({
    queryKey: computed(() => salesKeys.conversion(scope.value, id.value)),
    queryFn: ({ signal }) => salesApi.context(id.value, signal),
    enabled,
    retry: false,
  });
}
export function useSalesCatalog(
  search: Ref<string>,
  enabled: Ref<boolean>,
): UseQueryReturnType<CatalogChoice[], Error> {
  const scope = useSalesScope();
  return useQuery({
    queryKey: computed(() => salesKeys.catalog(scope.value, search.value)),
    queryFn: ({ signal }) => searchSalesCatalog(search.value, signal),
    enabled,
  });
}
export { useContactPointLabels };
export { useSalesScope } from "./sales.scope";

export function useSalesContactPreview(
  id: Ref<string | null>,
  enabled: Ref<boolean>,
): UseQueryReturnType<SourceContactPreview, Error> {
  const scope = useSalesScope();
  return useQuery({
    queryKey: computed(() => salesKeys.contactPreview(scope.value, id.value)),
    queryFn: async ({ signal }) => {
      const [contact, points] = await Promise.all([
        crmContactsApi.get(id.value!, signal),
        crmContactPointsApi.get("contacts", id.value!, signal),
      ]);
      return {
        name: contact.displayName,
        values: [...points.phones, ...points.emails].map((p) => p.value),
      };
    },
    enabled: computed(() => enabled.value && !!id.value),
  });
}
