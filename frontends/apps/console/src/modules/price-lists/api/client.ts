import { httpClient } from "@/app/providers/http/http-client";
import type {
  MappingConfig,
  OfferFilters,
  OfferHistoryFilters,
  OfferHistoryResponse,
  OffersResponse,
  PreviewResult,
  PriceList,
  PriceListScope,
  SourceFormat,
  SyncRun,
} from "./contracts";
import type {
  OffersResponseDto,
  OfferHistoryResponseDto,
  PreviewResultDto,
  PriceListDto,
  SyncRunDto,
} from "./price-lists.dto";
import {
  mapOfferHistory,
  mapOffers,
  mapPreview,
  mapPriceList,
  mapSyncRun,
} from "./price-lists.mapper";

export const priceListsApi = {
  async list(
    scope: PriceListScope = "current",
    signal?: AbortSignal,
  ): Promise<PriceList[]> {
    const { data } = await httpClient.get<{ items: PriceListDto[] }>(
      "/console/price-lists",
      { signal, params: { scope } },
    );
    return data.items.map(mapPriceList);
  },
  async get(id: string, signal?: AbortSignal): Promise<PriceList> {
    const { data } = await httpClient.get<PriceListDto>(
      `/console/price-lists/${id}`,
      { signal },
    );
    return mapPriceList(data);
  },
  async create(payload: {
    title: string;
    source_url: string;
    source_format: SourceFormat;
    source_preset: "prom_xml" | null;
    source_config: Record<string, unknown>;
  }): Promise<{ id: string }> {
    const { data } = await httpClient.post("/console/price-lists", payload);
    return data;
  },
  async preview(
    id: string,
    candidate?: {
      source_url?: string;
      source_format?: SourceFormat;
      source_preset?: "prom_xml" | null;
      source_config?: Record<string, unknown>;
      mapping_config?: MappingConfig;
    },
  ): Promise<PreviewResult> {
    const { data } = await httpClient.post<PreviewResultDto>(
      `/console/price-lists/${id}/preview`,
      candidate,
    );
    return mapPreview(data);
  },
  async saveMapping(
    id: string,
    sourceConfig: Record<string, unknown>,
    mappingConfig: MappingConfig,
  ): Promise<void> {
    await httpClient.put(`/console/price-lists/${id}/mapping`, {
      source_config: sourceConfig,
      mapping_config: mappingConfig,
    });
  },
  async saveSchedule(
    id: string,
    payload: {
      cron_expression: string;
      timezone: string;
      new_item_policy: "create" | "quarantine" | "ignore";
      missing_item_policy:
        "mark_out_of_stock" | "mark_missing" | "keep_last" | "archive";
      missing_threshold: number;
    },
  ): Promise<void> {
    await httpClient.put(`/console/price-lists/${id}/schedule`, payload);
  },
  async updateSettings(
    id: string,
    payload: {
      title: string;
      source_url?: string;
      source_format: SourceFormat;
      source_preset: "prom_xml" | null;
      source_config: Record<string, unknown>;
      mapping_config: MappingConfig;
      cron_expression: string;
      timezone: string;
      new_item_policy: "create" | "quarantine" | "ignore";
      missing_item_policy:
        "mark_out_of_stock" | "mark_missing" | "keep_last" | "archive";
      missing_threshold: number;
    },
  ): Promise<void> {
    await httpClient.put(`/console/price-lists/${id}/settings`, payload);
  },
  async previewSchedule(
    expression: string,
    timezone: string,
  ): Promise<string[]> {
    const params = new URLSearchParams({ expression, timezone });
    const { data } = await httpClient.get<{ occurrences: string[] }>(
      `/console/price-lists/schedule-preview?${params.toString()}`,
    );
    return data.occurrences;
  },
  async activate(id: string): Promise<void> {
    await httpClient.post(`/console/price-lists/${id}/activate`);
  },
  async action(
    id: string,
    action: "sync" | "pause" | "resume" | "archive" | "restore",
  ): Promise<void> {
    await httpClient.post(`/console/price-lists/${id}/${action}`);
  },
  async delete(id: string, confirmationTitle: string): Promise<void> {
    await httpClient.delete(`/console/price-lists/${id}`, {
      data: { confirmation_title: confirmationTitle },
    });
  },
  async runs(id: string, signal?: AbortSignal): Promise<SyncRun[]> {
    const { data } = await httpClient.get<{ items: SyncRunDto[] }>(
      `/console/price-lists/${id}/runs`,
      { signal },
    );
    return data.items.map(mapSyncRun);
  },
  async offers(
    filters: OfferFilters,
    signal?: AbortSignal,
  ): Promise<OffersResponse> {
    const params = new URLSearchParams();
    const pairs: Array<[string, string]> = [
      ["business_date", filters.businessDate],
      ["q", filters.q],
      ["price_list_id", filters.priceListId],
      ["purchase_price_min", filters.purchasePriceMin],
      ["purchase_price_max", filters.purchasePriceMax],
      ["recommended_retail_income_min", filters.incomeMin],
      ["recommended_retail_income_max", filters.incomeMax],
      ["margin_percent_min", filters.marginMin],
      ["margin_percent_max", filters.marginMax],
      ["availability", filters.availability],
      ["has_rrp", filters.hasRrp],
      ["sort", filters.sort],
      ["direction", filters.direction],
      ["offset", String((filters.page - 1) * filters.limit)],
      ["limit", String(filters.limit)],
      ["include_archived", filters.includeArchived ? "true" : ""],
    ];
    for (const [key, value] of pairs) if (value) params.set(key, value);
    const { data } = await httpClient.get<OffersResponseDto>(
      `/console/price-list-offers?${params.toString()}`,
      { signal },
    );
    return mapOffers(data);
  },
  async history(
    id: string,
    filters: OfferHistoryFilters,
    signal?: AbortSignal,
  ): Promise<OfferHistoryResponse> {
    const params = new URLSearchParams();
    const pairs: Array<[string, string]> = [
      [
        "observed_from",
        filters.observedFrom
          ? new Date(filters.observedFrom).toISOString()
          : "",
      ],
      [
        "observed_to",
        filters.observedTo ? new Date(filters.observedTo).toISOString() : "",
      ],
      ["purchase_price_min", filters.purchasePriceMin],
      ["purchase_price_max", filters.purchasePriceMax],
      ["rrp_min", filters.rrpMin],
      ["rrp_max", filters.rrpMax],
      ["recommended_retail_income_min", filters.incomeMin],
      ["recommended_retail_income_max", filters.incomeMax],
      ["margin_percent_min", filters.marginMin],
      ["margin_percent_max", filters.marginMax],
      ["quantity_min", filters.quantityMin],
      ["quantity_max", filters.quantityMax],
      ["availability", filters.availability],
      ["change_reason", filters.changeReason],
      ["sort", filters.sort],
      ["direction", filters.direction],
      ["offset", String((filters.page - 1) * filters.limit)],
      ["limit", String(filters.limit)],
    ];
    for (const [key, value] of pairs) if (value) params.set(key, value);
    const { data } = await httpClient.get<OfferHistoryResponseDto>(
      `/console/price-list-offers/${id}/history`,
      { signal, params },
    );
    return mapOfferHistory(data);
  },
};
