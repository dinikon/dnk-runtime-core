import { toValue, type MaybeRefOrGetter } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { catalogImportApi } from "../api/import.api";
import { importKeys } from "./import.query-keys";
import type {
  ImportConfiguration,
  ImportSourceValues,
  ImportActionResult,
} from "./import.types";
function useImportInvalidation(
  tenant: MaybeRefOrGetter<string>,
  session: MaybeRefOrGetter<string>,
): {
  snapshot: () => string[];
  refresh: (captured: string[] | undefined) => Promise<void>;
} {
  const cache = useQueryClient();
  return {
    snapshot: (): string[] => [toValue(tenant), toValue(session)],
    refresh: async (captured: string[] | undefined): Promise<void> => {
      if (
        !captured ||
        captured[0] !== toValue(tenant) ||
        captured[1] !== toValue(session)
      )
        return;
      await cache.invalidateQueries({
        queryKey: importKeys.all(captured[0]!, captured[1]!),
      });
    },
  };
}
export function useCreateCatalogImport(
  tenant: MaybeRefOrGetter<string>,
  session: MaybeRefOrGetter<string>,
): UseMutationReturnType<
  ImportActionResult,
  Error,
  ImportSourceValues,
  string[]
> {
  const update = useImportInvalidation(tenant, session);
  return useMutation({
    mutationFn: (value: ImportSourceValues) => catalogImportApi.create(value),
    retry: false,
    onMutate: update.snapshot,
    onSuccess: (_data, _variables, context) => update.refresh(context),
  });
}
export function useConfigureCatalogImport(
  tenant: MaybeRefOrGetter<string>,
  session: MaybeRefOrGetter<string>,
): UseMutationReturnType<
  ImportActionResult,
  Error,
  { id: string; configuration: ImportConfiguration },
  string[]
> {
  const update = useImportInvalidation(tenant, session);
  return useMutation({
    mutationFn: (value: { id: string; configuration: ImportConfiguration }) =>
      catalogImportApi.configure(value.id, value.configuration),
    retry: false,
    onMutate: update.snapshot,
    onSuccess: (_data, _variables, context) => update.refresh(context),
  });
}
export function useStartCatalogImport(
  tenant: MaybeRefOrGetter<string>,
  session: MaybeRefOrGetter<string>,
): UseMutationReturnType<
  ImportActionResult,
  Error,
  { id: string; version: number },
  string[]
> {
  const update = useImportInvalidation(tenant, session);
  return useMutation({
    mutationFn: (value: { id: string; version: number }) =>
      catalogImportApi.start(value.id, value.version),
    retry: false,
    onMutate: update.snapshot,
    onSuccess: (_data, _variables, context) => update.refresh(context),
  });
}
export function useCancelCatalogImport(
  tenant: MaybeRefOrGetter<string>,
  session: MaybeRefOrGetter<string>,
): UseMutationReturnType<ImportActionResult, Error, string, string[]> {
  const update = useImportInvalidation(tenant, session);
  return useMutation({
    mutationFn: (id: string) => catalogImportApi.cancel(id),
    retry: false,
    onMutate: update.snapshot,
    onSuccess: (_data, _variables, context) => update.refresh(context),
  });
}
export function useDownloadImportReport(): UseMutationReturnType<
  Blob,
  Error,
  string,
  unknown
> {
  return useMutation({
    mutationFn: (id: string) => catalogImportApi.report(id),
    retry: false,
  });
}
