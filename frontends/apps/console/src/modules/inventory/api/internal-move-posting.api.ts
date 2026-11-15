import type { ListInternalMoveDestinationsResponseDTO } from "./internal-move-posting.dto";
import type {
  InternalMoveDestinations,
  InternalMoveDestinationParams,
} from "../model/internal-move-posting.types";
import { internalMoveDestinationsFromDto } from "./internal-move-posting.mapper";
import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import type {
  PrepareInternalMoveResponseDTO,
  ListInternalMoveSourcesResponseDTO,
  ListInternalMoveExecutionsResponseDTO,
  PostInternalMoveResponseDTO,
} from "./internal-move-posting.dto";
import {
  internalMovePreparationFromDto,
  internalMoveSourcesFromDto,
  internalMoveHistoryFromDto,
  internalMoveExecutionToDto,
  internalMoveResultFromDto,
} from "./internal-move-posting.mapper";
import type {
  InternalMovePreparation,
  InternalMoveSources,
  InternalMoveSourceParams,
  InternalMoveExecutionHistory,
  InternalMoveExecutionValues,
  InternalMovePostingResult,
  InternalMoveExecutionErrors,
} from "../model/internal-move-posting.types";
import { InternalMovePostingRequestError } from "../model/internal-move-posting.errors";
const root = "/console/inventory/stock-documents/internal-moves";
function fail(cause: unknown, values?: InternalMoveExecutionValues): never {
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
      : getApiErrorMessage(cause, "Не удалось выполнить действие перемещения.");
  const fields: InternalMoveExecutionErrors = { rows: {}, lines: {} };
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
    for (const internalMove of raw) {
      if (
        typeof internalMove !== "object" ||
        internalMove === null ||
        !Array.isArray(internalMove.loc)
      )
        continue;
      const index = internalMove.loc.indexOf("lines"),
        position: unknown = internalMove.loc[index + 1];
      if (index >= 0 && typeof position === "number" && rows[position])
        fields.rows[rows[position].key] =
          typeof internalMove.msg === "string"
            ? internalMove.msg
            : "Проверьте распределение.";
    }
  throw new InternalMovePostingRequestError(
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
export async function prepareInternalMove(
  id: string,
  signal?: AbortSignal,
): Promise<InternalMovePreparation> {
  try {
    return internalMovePreparationFromDto(
      (
        await httpClient.get<PrepareInternalMoveResponseDTO>(
          `${root}/${encodeURIComponent(id)}/move-context`,
          { signal },
        )
      ).data,
    );
  } catch (e: unknown) {
    return fail(e);
  }
}
export async function listInternalMoveSources(
  id: string,
  params: InternalMoveSourceParams,
  signal?: AbortSignal,
): Promise<InternalMoveSources> {
  try {
    return internalMoveSourcesFromDto(
      (
        await httpClient.get<ListInternalMoveSourcesResponseDTO>(
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
export async function listInternalMoveExecutions(
  id: string,
  offset: number,
  signal?: AbortSignal,
): Promise<InternalMoveExecutionHistory> {
  try {
    return internalMoveHistoryFromDto(
      (
        await httpClient.get<ListInternalMoveExecutionsResponseDTO>(
          `${root}/${encodeURIComponent(id)}/executions`,
          { params: { offset, limit: 20 }, signal },
        )
      ).data,
    );
  } catch (e: unknown) {
    return fail(e);
  }
}
export async function postInternalMove(
  id: string,
  values: InternalMoveExecutionValues,
  key: string,
  signal: AbortSignal,
): Promise<InternalMovePostingResult> {
  try {
    return internalMoveResultFromDto(
      (
        await httpClient.post<PostInternalMoveResponseDTO>(
          `${root}/${encodeURIComponent(id)}/move`,
          internalMoveExecutionToDto(values),
          { headers: { "Idempotency-Key": key }, signal },
        )
      ).data,
    );
  } catch (e: unknown) {
    return fail(e, values);
  }
}

export async function listInternalMoveDestinations(
  id: string,
  params: InternalMoveDestinationParams,
  signal?: AbortSignal,
): Promise<InternalMoveDestinations> {
  try {
    const response =
      await httpClient.get<ListInternalMoveDestinationsResponseDTO>(
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
      );
    return internalMoveDestinationsFromDto(response.data);
  } catch (cause: unknown) {
    return fail(cause);
  }
}
