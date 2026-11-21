import { returnDestinationsFromDto } from "./return-posting.mapper";
import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import type {
  PrepareReturnResponseDTO,
  ListReturnSourcesResponseDTO,
  ListReturnExecutionsResponseDTO,
  PostReturnResponseDTO,
} from "./return-posting.dto";
import {
  returnPreparationFromDto,
  returnSourcesFromDto,
  returnHistoryFromDto,
  returnExecutionToDto,
  returnResultFromDto,
} from "./return-posting.mapper";
import type {
  ReturnPreparation,
  ReturnSources,
  ReturnSourceParams,
  ReturnExecutionHistory,
  ReturnExecutionValues,
  ReturnPostingResult,
  ReturnExecutionErrors,
} from "../model/return-posting.types";
import { ReturnPostingRequestError } from "../model/return-posting.errors";
const root = "/console/inventory/stock-documents/returns";
function fail(cause: unknown, values?: ReturnExecutionValues): never {
  if (isCancel(cause)) throw cause;
  const raw: unknown = isAxiosError(cause)
    ? cause.response?.data?.detail
    : undefined;
  const detail =
    typeof raw === "object" && raw !== null && !Array.isArray(raw)
      ? raw
      : undefined;
  const message =
    detail && "message" in detail && typeof detail.message === "string"
      ? detail.message
      : getApiErrorMessage(cause, "Не удалось выполнить действие возврата.");
  const fields: ReturnExecutionErrors = { rows: {}, lines: {} };
  if (
    detail &&
    "position_id" in detail &&
    typeof detail.position_id === "string" &&
    values
  ) {
    const quantity =
      "current_quantity" in detail &&
      typeof detail.current_quantity === "string"
        ? detail.current_quantity
        : null;
    const unit =
      "base_uom" in detail && typeof detail.base_uom === "string"
        ? detail.base_uom
        : "";
    for (const row of values.rows.filter(
      (v) => v.selected && v.source?.id === detail.position_id,
    ))
      fields.rows[row.key] =
        quantity !== null
          ? `${message} Сейчас физически: ${quantity} ${unit}. Обновите сведения.`
          : message;
  }
  if (
    detail &&
    "document_line_id" in detail &&
    typeof detail.document_line_id === "string"
  )
    fields.lines[detail.document_line_id] = message;
  const rows = values?.rows.filter((v) => v.selected) ?? [];
  if (Array.isArray(raw))
    for (const issue of raw) {
      if (
        typeof issue !== "object" ||
        issue === null ||
        !Array.isArray(issue.loc)
      )
        continue;
      const index = issue.loc.indexOf("lines"),
        position: unknown = issue.loc[index + 1];
      if (index >= 0 && typeof position === "number" && rows[position])
        fields.rows[rows[position].key] =
          typeof issue.msg === "string"
            ? issue.msg
            : "Проверьте распределение.";
    }
  if (
    detail &&
    "origin_execution_line_id" in detail &&
    typeof detail.origin_execution_line_id === "string" &&
    values
  )
    for (const row of values.rows.filter(
      (v) =>
        v.selected &&
        v.originExecutionLineId === detail.origin_execution_line_id,
    ))
      fields.rows[row.key] = message;
  throw new ReturnPostingRequestError(
    message,
    getApiErrorStatus(cause) ?? undefined,
    detail && "code" in detail && typeof detail.code === "string"
      ? detail.code
      : undefined,
    detail &&
      "actual_version" in detail &&
      typeof detail.actual_version === "number"
      ? detail.actual_version
      : undefined,
    fields,
  );
}
export async function prepareReturn(
  id: string,
  signal?: AbortSignal,
): Promise<ReturnPreparation> {
  try {
    return returnPreparationFromDto(
      (
        await httpClient.get<PrepareReturnResponseDTO>(
          `${root}/${encodeURIComponent(id)}/return-context`,
          { signal },
        )
      ).data,
    );
  } catch (e: unknown) {
    return fail(e);
  }
}
export async function listReturnSources(
  id: string,
  params: ReturnSourceParams,
  signal?: AbortSignal,
): Promise<ReturnSources> {
  try {
    return returnSourcesFromDto(
      (
        await httpClient.get<ListReturnSourcesResponseDTO>(
          `${root}/${encodeURIComponent(id)}/source-positions`,
          {
            params: {
              document_line_id: params.documentLineId,
              search: params.search.trim() || undefined,
              offset: params.offset,
              limit: 20,
              position_id: params.positionId,
            },
            signal,
          },
        )
      ).data,
    );
  } catch (e: unknown) {
    return fail(e);
  }
}
export async function listReturnExecutions(
  id: string,
  offset: number,
  signal?: AbortSignal,
): Promise<ReturnExecutionHistory> {
  try {
    return returnHistoryFromDto(
      (
        await httpClient.get<ListReturnExecutionsResponseDTO>(
          `${root}/${encodeURIComponent(id)}/executions`,
          { params: { offset, limit: 20 }, signal },
        )
      ).data,
    );
  } catch (e: unknown) {
    return fail(e);
  }
}
export async function postReturn(
  id: string,
  values: ReturnExecutionValues,
  key: string,
  signal: AbortSignal,
): Promise<ReturnPostingResult> {
  try {
    return returnResultFromDto(
      (
        await httpClient.post<PostReturnResponseDTO>(
          `${root}/${encodeURIComponent(id)}/return`,
          returnExecutionToDto(values),
          { headers: { "Idempotency-Key": key }, signal },
        )
      ).data,
    );
  } catch (e: unknown) {
    return fail(e, values);
  }
}

import type { ReturnPreviewResponseDTO } from "./return-preview.dto";
import { returnPreviewFromDto } from "./return-preview.mapper";
import type { ReturnPreview } from "../model/return-preview.types";
export async function previewReturn(
  id: string,
  values: ReturnExecutionValues,
  signal: AbortSignal,
): Promise<ReturnPreview> {
  try {
    return returnPreviewFromDto(
      (
        await httpClient.post<ReturnPreviewResponseDTO>(
          `${root}/${encodeURIComponent(id)}/preview`,
          returnExecutionToDto(values),
          { signal },
        )
      ).data,
    );
  } catch (e: unknown) {
    return fail(e, values);
  }
}

import type { ListReturnDestinationsResponseDTO } from "./return-posting.dto";
import type {
  ReturnDestinations,
  ReturnDestinationParams,
} from "../model/return-posting.types";
export async function listReturnDestinations(
  id: string,
  params: ReturnDestinationParams,
  signal: AbortSignal,
): Promise<ReturnDestinations> {
  try {
    return returnDestinationsFromDto(
      (
        await httpClient.get<ListReturnDestinationsResponseDTO>(
          `${root}/${encodeURIComponent(id)}/destination-locations`,
          {
            params: {
              search: params.search.trim() || undefined,
              offset: params.offset,
              limit: 20,
              location_id: params.locationId,
            },
            signal,
          },
        )
      ).data,
    );
  } catch (e: unknown) {
    return fail(e);
  }
}
