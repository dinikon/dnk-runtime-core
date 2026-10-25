import { httpClient } from "@/app/providers/http";
import {
  mapLeadRow,
  mapDealRow,
  mapLead,
  mapDeal,
  mapContext,
  mapConversion,
  leadPayload,
  dealPayload,
  conversionPayload,
} from "./sales.mapper";
import type {
  LeadPageDto,
  DealPageDto,
  LeadDetailsDto,
  DealDetailsDto,
  SaleMutationDto,
  ConversionContextDto,
  ConversionResultDto,
} from "./sales.dto";
import type {
  SalesKind,
  SalesPage,
  SaleRecord,
  SaleDraft,
  ConversionContext,
  ConversionSubmission,
  ConversionResult,
} from "../model/sales.types";
const root = (kind: SalesKind) => "/console/crm/" + kind;
export const salesApi = {
  async list(
    kind: SalesKind,
    filters: {
      funnelId: string;
      stageId?: string;
      search: string;
      converted?: boolean;
      offset: number;
      sort: string;
    },
    signal?: AbortSignal,
  ): Promise<SalesPage> {
    const params = {
      funnel_id: filters.funnelId,
      stage_id: filters.stageId || undefined,
      search: filters.search,
      converted: filters.converted,
      offset: filters.offset,
      limit: 20,
      sort: filters.sort,
    };
    if (kind === "leads") {
      const { data } = await httpClient.get<LeadPageDto>(root(kind), {
        params,
        signal,
      });
      return { ...data, items: data.items.map(mapLeadRow) };
    }
    const { data } = await httpClient.get<DealPageDto>(root(kind), {
      params,
      signal,
    });
    return { ...data, items: data.items.map(mapDealRow) };
  },
  async get(
    kind: SalesKind,
    id: string,
    signal?: AbortSignal,
  ): Promise<SaleRecord> {
    if (kind === "leads")
      return mapLead(
        (
          await httpClient.get<LeadDetailsDto>(
            root(kind) + "/" + encodeURIComponent(id),
            {
              signal,
            },
          )
        ).data,
      );
    return mapDeal(
      (
        await httpClient.get<DealDetailsDto>(
          root(kind) + "/" + encodeURIComponent(id),
          { signal },
        )
      ).data,
    );
  },
  async create(kind: SalesKind, v: SaleDraft): Promise<{ id: string }> {
    return (
      await httpClient.post<SaleMutationDto>(root(kind), {
        ...(kind === "leads" ? leadPayload(v) : dealPayload(v)),
        funnel_id: v.funnelId || null,
      })
    ).data;
  },
  async update(
    kind: SalesKind,
    id: string,
    v: SaleDraft,
    previous: SaleDraft,
  ): Promise<{ lineIdMap: Record<string, string> }> {
    const before =
        kind === "leads" ? leadPayload(previous) : dealPayload(previous),
      after = kind === "leads" ? leadPayload(v) : dealPayload(v);
    const payload: Record<string, unknown> = {};
    for (const key of Object.keys(after) as (keyof typeof after)[]) {
      if (JSON.stringify(after[key]) !== JSON.stringify(before[key]))
        payload[key] = after[key];
    }
    if (!Object.keys(payload).length) return { lineIdMap: {} };
    const { data } = await httpClient.patch<SaleMutationDto>(
      root(kind) + "/" + encodeURIComponent(id),
      payload,
    );
    return { lineIdMap: data.line_id_map };
  },
  async move(
    kind: SalesKind,
    id: string,
    stageId: string,
    revision: number,
  ): Promise<void> {
    await httpClient.put(root(kind) + "/" + encodeURIComponent(id) + "/stage", {
      stage_id: stageId,
      expected_position_revision: revision,
    });
  },
  async changeFunnel(
    kind: SalesKind,
    id: string,
    funnelId: string,
    revision: number,
  ): Promise<void> {
    await httpClient.put(
      root(kind) + "/" + encodeURIComponent(id) + "/funnel",
      {
        funnel_id: funnelId,
        expected_position_revision: revision,
      },
    );
  },
  async context(id: string, signal?: AbortSignal): Promise<ConversionContext> {
    return mapContext(
      (
        await httpClient.get<ConversionContextDto>(
          "/console/crm/leads/" +
            encodeURIComponent(id) +
            "/conversion-context",
          { signal },
        )
      ).data,
    );
  },
  async convert(
    id: string,
    v: ConversionSubmission,
    key: string,
  ): Promise<ConversionResult> {
    return mapConversion(
      (
        await httpClient.post<ConversionResultDto>(
          "/console/crm/leads/" + encodeURIComponent(id) + "/convert",
          conversionPayload(v),
          { headers: { "Idempotency-Key": key } },
        )
      ).data,
    );
  },
};
