import { computed } from "vue";
import { useSalesScope } from "./sales.scope";
import { salesKeys } from "./sales.query-keys";
import type { UseMutationReturnType } from "@tanstack/vue-query";
import type {
  ContactSeed,
  CreateSaleInput,
  UpdateSaleInput,
  MoveSaleInput,
  ConvertLeadInput,
  SaveSaleResult,
  SaleRecord,
  ConversionResult,
  CatalogChoice,
} from "./sales.types";
import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { salesApi } from "../api/sales.api";
import { crmContactsApi, crmContactPointsApi } from "../api/crm.api";
import { readSalesCatalog } from "@/modules/catalog";
import type {
  SalesKind,
  SaleDraft,
  ConversionSubmission,
  SaleSummary,
} from "./sales.types";
interface SalesMutations {
  create: UseMutationReturnType<
    { id: string },
    Error,
    CreateSaleInput,
    unknown
  >;
  update: UseMutationReturnType<
    SaveSaleResult,
    Error,
    UpdateSaleInput,
    unknown
  >;
  position: UseMutationReturnType<void, Error, MoveSaleInput, unknown>;
  convert: UseMutationReturnType<
    ConversionResult,
    Error,
    ConvertLeadInput,
    unknown
  >;
  refresh: () => Promise<void>;
  verify: (kind: SalesKind, id: string) => Promise<SaleRecord>;
}
export function useSalesMutations(): SalesMutations {
  const client = useQueryClient(),
    scope = useSalesScope();
  async function refresh(): Promise<void> {
    await client.invalidateQueries({
      predicate: (q) =>
        (String(q.queryKey[0]).startsWith("sales-") &&
          q.queryKey[0] !== "sales-conversion") ||
        q.queryKey[0] === "crm",
    });
  }
  const create = useMutation({
    mutationKey: computed(() => ["sales-create", ...scope.value]),
    mutationFn: (v: { kind: SalesKind; draft: SaleDraft }) =>
      salesApi.create(v.kind, v.draft),
    onSuccess: refresh,
  });
  const update = useMutation({
    mutationKey: computed(() => ["sales-update", ...scope.value]),
    mutationFn: (v: {
      kind: SalesKind;
      id: string;
      draft: SaleDraft;
      previous: SaleDraft;
    }) => salesApi.update(v.kind, v.id, v.draft, v.previous),
    onSuccess: refresh,
  });
  const position = useMutation({
    mutationKey: computed(() => ["sales-position", ...scope.value]),
    mutationFn: (v: {
      record: SaleSummary;
      stageId?: string;
      funnelId?: string;
    }) =>
      v.funnelId
        ? salesApi.changeFunnel(
            v.record.kind,
            v.record.id,
            v.funnelId,
            v.record.positionRevision,
          )
        : salesApi.move(
            v.record.kind,
            v.record.id,
            v.stageId!,
            v.record.positionRevision,
          ),
    onSuccess: refresh,
  });
  const convert = useMutation({
    mutationKey: computed(() => ["sales-convert", ...scope.value]),
    mutationFn: (v: {
      id: string;
      submission: ConversionSubmission;
      key: string;
    }) => salesApi.convert(v.id, v.submission, v.key),
    onSuccess: refresh,
  });
  async function verify(kind: SalesKind, id: string): Promise<SaleRecord> {
    return await client.fetchQuery({
      queryKey: salesKeys.detail(scope.value, kind, id),
      queryFn: ({ signal }) => salesApi.get(kind, id, signal),
      staleTime: 0,
      retry: false,
    });
  }
  return { create, update, position, convert, refresh, verify };
}
export function useSalesContactSeed(): UseMutationReturnType<
  ContactSeed,
  Error,
  string,
  unknown
> {
  const scope = useSalesScope();
  return useMutation({
    mutationKey: computed(() => ["sales-copy", ...scope.value]),
    mutationFn: async (id: string) => ({
      contact: await crmContactsApi.get(id),
      points: await crmContactPointsApi.get("contacts", id),
    }),
  });
}

export function useSalesCatalogSelection(): UseMutationReturnType<
  CatalogChoice,
  Error,
  string,
  unknown
> {
  const scope = useSalesScope();
  return useMutation({
    mutationKey: computed(() => ["sales-select", ...scope.value]),
    mutationFn: (id: string) => readSalesCatalog(id),
  });
}
