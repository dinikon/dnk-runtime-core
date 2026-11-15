import type {
  ListStockBalancesResult,
  StockBalancesParams,
} from "../model/stock-accounting.types";
import type { ListStockBalancesResultDTO } from "./stock-accounting.dto";
import { listStockBalancesResultFromDto } from "./stock-accounting.mapper";
import { isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import type { StockReadParams } from "../model/stock-accounting.types";
import type {
  ListStockPositionsResult,
  GetStockPositionResult,
  ListStockMovementsResult,
  ListStockExecutionsResult,
  ListStockPostingsResult,
  GetStockExecutionDetailsResult,
  GetStockPostingDetailsResult,
} from "../model/stock-accounting.types";
import type {
  ListStockPositionsResultDTO,
  GetStockPositionResultDTO,
  ListStockMovementsResultDTO,
  ListStockExecutionsResultDTO,
  ListStockPostingsResultDTO,
  GetStockExecutionDetailsResultDTO,
  GetStockPostingDetailsResultDTO,
} from "./stock-accounting.dto";
import {
  listStockPositionsResultFromDto,
  getStockPositionResultFromDto,
  listStockMovementsResultFromDto,
  listStockExecutionsResultFromDto,
  listStockPostingsResultFromDto,
  getStockExecutionDetailsResultFromDto,
  getStockPostingDetailsResultFromDto,
} from "./stock-accounting.mapper";
export class StockAccountingRequestError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "StockAccountingRequestError";
  }
}
export function stockReadParams(
  params: StockReadParams,
): Record<string, string | number | boolean | undefined> {
  return {
    offset: params.offset,
    limit: params.limit,
    warehouse_id: params.filters.warehouseId,
    location_id: params.filters.locationId,
    owner_id: params.filters.ownerId,
    inventory_item_id: params.filters.inventoryItemId,
    lot_id: params.filters.lotId,
    serial_id: params.filters.serialId,
    position_id: params.filters.positionId,
    document_id: params.filters.documentId,
    execution_id: params.filters.executionId,
    posting_id: params.filters.postingId,
    stock_status: params.filters.stockStatus,
    operation_type: params.filters.operationType,
    posted_from: params.filters.postedFrom,
    posted_to: params.filters.postedTo,
    search: params.filters.search,
    ...(params.filters.includeZero !== undefined
      ? { include_zero: params.filters.includeZero }
      : {}),
  };
}
async function read<Dto, Model>(
  path: string,
  mapper: (value: Dto) => Model,
  signal?: AbortSignal,
  params?: Record<string, string | number | boolean | undefined>,
): Promise<Model> {
  try {
    return mapper(
      (
        await httpClient.get<Dto>("/console/inventory/" + path, {
          signal,
          params,
        })
      ).data,
    );
  } catch (cause: unknown) {
    if (isCancel(cause)) throw cause;
    throw new StockAccountingRequestError(
      getApiErrorMessage(cause, "Не удалось загрузить физический учёт."),
      getApiErrorStatus(cause) ?? undefined,
    );
  }
}
export function listStockPositions(
  params: StockReadParams,
  signal?: AbortSignal,
): Promise<ListStockPositionsResult> {
  return read<ListStockPositionsResultDTO, ListStockPositionsResult>(
    `stock-positions`,
    listStockPositionsResultFromDto,
    signal,
    stockReadParams(params),
  );
}
export function getStockPosition(
  id: string,
  signal?: AbortSignal,
): Promise<GetStockPositionResult> {
  return read<GetStockPositionResultDTO, GetStockPositionResult>(
    `stock-positions/${encodeURIComponent(id)}`,
    getStockPositionResultFromDto,
    signal,
  );
}
export function listStockMovements(
  params: StockReadParams,
  signal?: AbortSignal,
): Promise<ListStockMovementsResult> {
  return read<ListStockMovementsResultDTO, ListStockMovementsResult>(
    `stock-movements`,
    listStockMovementsResultFromDto,
    signal,
    stockReadParams(params),
  );
}
export function listStockExecutions(
  params: StockReadParams,
  signal?: AbortSignal,
): Promise<ListStockExecutionsResult> {
  return read<ListStockExecutionsResultDTO, ListStockExecutionsResult>(
    `stock-executions`,
    listStockExecutionsResultFromDto,
    signal,
    stockReadParams(params),
  );
}
export function listStockPostings(
  params: StockReadParams,
  signal?: AbortSignal,
): Promise<ListStockPostingsResult> {
  return read<ListStockPostingsResultDTO, ListStockPostingsResult>(
    `stock-postings`,
    listStockPostingsResultFromDto,
    signal,
    stockReadParams(params),
  );
}
export function getStockExecutionDetails(
  id: string,
  signal?: AbortSignal,
): Promise<GetStockExecutionDetailsResult> {
  return read<
    GetStockExecutionDetailsResultDTO,
    GetStockExecutionDetailsResult
  >(
    `stock-executions/${encodeURIComponent(id)}/details`,
    getStockExecutionDetailsResultFromDto,
    signal,
  );
}
export function getStockPostingDetails(
  id: string,
  signal?: AbortSignal,
): Promise<GetStockPostingDetailsResult> {
  return read<GetStockPostingDetailsResultDTO, GetStockPostingDetailsResult>(
    `stock-postings/${encodeURIComponent(id)}/details`,
    getStockPostingDetailsResultFromDto,
    signal,
  );
}

export function listStockBalances(
  params: StockBalancesParams,
  signal?: AbortSignal,
): Promise<ListStockBalancesResult> {
  return read<ListStockBalancesResultDTO, ListStockBalancesResult>(
    "stock-balances",
    listStockBalancesResultFromDto,
    signal,
    {
      ...stockReadParams(params),
      group_by_lot: params.groupByLot,
      group_by_serial: params.groupBySerial,
    },
  );
}
