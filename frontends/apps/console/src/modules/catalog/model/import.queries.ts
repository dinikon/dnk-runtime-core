import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { catalogImportApi } from "../api/import.api";
import { importKeys } from "./import.query-keys";
import { importIsActive } from "./import.constants";
import type {
  ImportPage,
  ImportRowsPage,
  CatalogImportDetails,
} from "./import.types";
export function useCatalogImportsQuery(
  tenant: MaybeRefOrGetter<string>,
  session: MaybeRefOrGetter<string>,
  page: MaybeRefOrGetter<number>,
): UseQueryReturnType<ImportPage, Error> {
  return useQuery({
    queryKey: computed(() =>
      importKeys.list(toValue(tenant), toValue(session), toValue(page)),
    ),
    enabled: computed(() => !!toValue(tenant)),
    queryFn: ({ signal }) => catalogImportApi.list(toValue(page), signal),
    refetchInterval: (query) =>
      query.state.data?.items.some((run) => importIsActive(run.status))
        ? 2000
        : false,
  });
}
export function useCatalogImportQuery(
  tenant: MaybeRefOrGetter<string>,
  session: MaybeRefOrGetter<string>,
  id: MaybeRefOrGetter<string>,
): UseQueryReturnType<CatalogImportDetails, Error> {
  return useQuery({
    queryKey: computed(() =>
      importKeys.detail(toValue(tenant), toValue(session), toValue(id)),
    ),
    enabled: computed(() => !!toValue(tenant) && !!toValue(id)),
    queryFn: ({ signal }) => catalogImportApi.get(toValue(id), signal),
    refetchInterval: (query) =>
      query.state.data && importIsActive(query.state.data.run.status)
        ? 2000
        : false,
  });
}
export function useCatalogImportRowsQuery(
  tenant: MaybeRefOrGetter<string>,
  session: MaybeRefOrGetter<string>,
  id: MaybeRefOrGetter<string>,
  page: MaybeRefOrGetter<number>,
  outcome: MaybeRefOrGetter<string>,
  active: MaybeRefOrGetter<boolean>,
): UseQueryReturnType<ImportRowsPage, Error> {
  return useQuery({
    queryKey: computed(() =>
      importKeys.rows(
        toValue(tenant),
        toValue(session),
        toValue(id),
        toValue(page),
        toValue(outcome),
      ),
    ),
    enabled: computed(
      () => !!toValue(tenant) && !!toValue(id) && toValue(active),
    ),
    queryFn: ({ signal }) =>
      catalogImportApi.rows(
        toValue(id),
        toValue(page),
        toValue(outcome),
        signal,
      ),
    refetchInterval: false,
  });
}
