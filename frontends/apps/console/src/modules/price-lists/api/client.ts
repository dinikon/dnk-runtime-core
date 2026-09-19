import { httpClient } from "@/app/providers/http/http-client";
import type {
  MappingConfig,
  OfferFilters,
  OffersResponse,
  PartnerOfferState,
  PreviewResult,
  PriceList,
  SourceFormat,
  SyncRun,
} from "./contracts";
import type {
  OffersResponseDto,
  PartnerOfferStateDto,
  PreviewResultDto,
  PriceListDto,
  SyncRunDto,
} from "./price-lists.dto";
import {
  mapOfferState,
  mapOffers,
  mapPreview,
  mapPriceList,
  mapSyncRun,
} from "./price-lists.mapper";

export const priceListsApi = {
  async list(signal?: AbortSignal): Promise<PriceList[]> {
    const { data } = await httpClient.get<{ items: PriceListDto[] }>(
      "/console/price-lists",
      { signal },
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
  async preview(id: string): Promise<PreviewResult> {
    const { data } = await httpClient.post<PreviewResultDto>(
      `/console/price-lists/${id}/preview`,
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
      missing_item_policy: "mark_out_of_stock" | "mark_missing" | "keep_last" | "archive";
      missing_threshold: number;
    },
  ): Promise<void> {
    await httpClient.put(`/console/price-lists/${id}/schedule`, payload);
  },
  async previewSchedule(expression: string, timezone: string): Promise<string[]> {
    const params = new URLSearchParams({ expression, timezone });
    const { data } = await httpClient.get<{ occurrences: string[] }>(
      `/console/price-lists/schedule-preview?${params.toString()}`,
    );
    return data.occurrences;
  },
  async activate(id: string): Promise<void> {
    await httpClient.post(`/console/price-lists/${id}/activate`);
  },
  async action(id: string, action: "sync" | "pause" | "resume"): Promise<void> {
    await httpClient.post(`/console/price-lists/${id}/${action}`);
  },
  async runs(id: string, signal?: AbortSignal): Promise<SyncRun[]> {
    const { data } = await httpClient.get<{ items: SyncRunDto[] }>(
      `/console/price-lists/${id}/runs`,
      { signal },
    );
    return data.items.map(mapSyncRun);
  },
  async offers(filters: OfferFilters, signal?: AbortSignal): Promise<OffersResponse> {
    const params = new URLSearchParams();
    const pairs: Array<[string, string]> = [
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
    ];
    for (const [key, value] of pairs) if (value) params.set(key, value);
    const { data } = await httpClient.get<OffersResponseDto>(
      `/console/price-list-offers?${params.toString()}`,
      { signal },
    );
    return mapOffers(data);
  },
  async history(id: string): Promise<{ items: PartnerOfferState[] }> {
    const { data } = await httpClient.get<{ items: PartnerOfferStateDto[] }>(
      `/console/price-list-offers/${id}/history`,
    );
    return { items: data.items.map(mapOfferState) };
  },
};
