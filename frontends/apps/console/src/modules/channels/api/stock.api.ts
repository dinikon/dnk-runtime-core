import { httpClient } from "@/app/providers/http";
import { channelRequest } from "./channel.api";
import type {
  BindingStockDto,
  RefreshPublicationStockResponseDto,
  ExportCatalogStockResponseDto,
} from "./stock.dto";
import {
  mapBindingStock,
  refreshStockPayload,
  exportStockPayload,
} from "./stock.mapper";
import type { BindingStock, StockRequest } from "../model/stock.types";
const root = (channel: string, group: string): string =>
  `/console/channels/${encodeURIComponent(channel)}/catalog-bindings/${encodeURIComponent(group)}`;
export const stockApi = {
  async get(
    channel: string,
    group: string,
    signal?: AbortSignal,
  ): Promise<BindingStock> {
    return channelRequest(async () =>
      mapBindingStock(
        (
          await httpClient.get<BindingStockDto>(
            `${root(channel, group)}/stock`,
            { signal },
          )
        ).data,
      ),
    );
  },
  async refresh(value: StockRequest): Promise<string[]> {
    return channelRequest(
      async () =>
        (
          await httpClient.post<RefreshPublicationStockResponseDto>(
            `${root(value.channelId, value.groupId)}/stock-import`,
            refreshStockPayload(value),
          )
        ).data.operation_ids,
    );
  },
  async export(value: StockRequest): Promise<string[]> {
    return channelRequest(
      async () =>
        (
          await httpClient.post<ExportCatalogStockResponseDto>(
            `${root(value.channelId, value.groupId)}/stock-export`,
            exportStockPayload(),
          )
        ).data.operation_ids,
    );
  },
};
