import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import type {
  PrepareStatusChangeResponseDTO,
  ListStatusChangeSourcesResponseDTO,
  ListStatusChangeExecutionsResponseDTO,
  PostStatusChangeResponseDTO,
} from "./status-change-posting.dto";
import {
  statusChangePreparationFromDto,
  statusChangeSourcesFromDto,
  statusChangeHistoryFromDto,
  statusChangeExecutionToDto,
  statusChangeResultFromDto,
} from "./status-change-posting.mapper";
import type {
  StatusChangePreparation,
  StatusChangeSources,
  StatusChangeSourceParams,
  StatusChangeExecutionHistory,
  StatusChangeExecutionValues,
  StatusChangePostingResult,
  StatusChangeExecutionErrors,
} from "../model/status-change-posting.types";
import { StatusChangePostingRequestError } from "../model/status-change-posting.errors";
const root = "/console/inventory/stock-documents/status-changes";
function fail(cause: unknown, values?: StatusChangeExecutionValues): never {
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
      : getApiErrorMessage(
          cause,
          "Не удалось выполнить действие изменения состояния.",
        );
  const fields: StatusChangeExecutionErrors = { rows: {}, lines: {} };
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
    for (const statusChange of raw) {
      if (
        typeof statusChange !== "object" ||
        statusChange === null ||
        !Array.isArray(statusChange.loc)
      )
        continue;
      const index = statusChange.loc.indexOf("lines"),
        position: unknown = statusChange.loc[index + 1];
      if (index >= 0 && typeof position === "number" && rows[position])
        fields.rows[rows[position].key] =
          typeof statusChange.msg === "string"
            ? statusChange.msg
            : "Проверьте распределение.";
    }
  throw new StatusChangePostingRequestError(
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
export async function prepareStatusChange(
  id: string,
  signal?: AbortSignal,
): Promise<StatusChangePreparation> {
  try {
    return statusChangePreparationFromDto(
      (
        await httpClient.get<PrepareStatusChangeResponseDTO>(
          `${root}/${encodeURIComponent(id)}/status-change-context`,
          { signal },
        )
      ).data,
    );
  } catch (e: unknown) {
    return fail(e);
  }
}
export async function listStatusChangeSources(
  id: string,
  params: StatusChangeSourceParams,
  signal?: AbortSignal,
): Promise<StatusChangeSources> {
  try {
    return statusChangeSourcesFromDto(
      (
        await httpClient.get<ListStatusChangeSourcesResponseDTO>(
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
export async function listStatusChangeExecutions(
  id: string,
  offset: number,
  signal?: AbortSignal,
): Promise<StatusChangeExecutionHistory> {
  try {
    return statusChangeHistoryFromDto(
      (
        await httpClient.get<ListStatusChangeExecutionsResponseDTO>(
          `${root}/${encodeURIComponent(id)}/executions`,
          { params: { offset, limit: 20 }, signal },
        )
      ).data,
    );
  } catch (e: unknown) {
    return fail(e);
  }
}
export async function postStatusChange(
  id: string,
  values: StatusChangeExecutionValues,
  key: string,
  signal: AbortSignal,
): Promise<StatusChangePostingResult> {
  try {
    return statusChangeResultFromDto(
      (
        await httpClient.post<PostStatusChangeResponseDTO>(
          `${root}/${encodeURIComponent(id)}/change-status`,
          statusChangeExecutionToDto(values),
          { headers: { "Idempotency-Key": key }, signal },
        )
      ).data,
    );
  } catch (e: unknown) {
    return fail(e, values);
  }
}

import type {
  StatusChangePreviewResponseDTO,
  StatusTransitionsResponseDTO,
} from "./status-change-preview.dto";
import {
  statusChangePreviewFromDto,
  statusTransitionsFromDto,
} from "./status-change-preview.mapper";
import type {
  StatusChangePreview,
  StatusTransition,
} from "../model/status-change-preview.types";
export async function previewStatusChange(
  id: string,
  values: StatusChangeExecutionValues,
  signal: AbortSignal,
): Promise<StatusChangePreview> {
  try {
    return statusChangePreviewFromDto(
      (
        await httpClient.post<StatusChangePreviewResponseDTO>(
          `${root}/${encodeURIComponent(id)}/preview`,
          statusChangeExecutionToDto(values),
          { signal },
        )
      ).data,
    );
  } catch (e: unknown) {
    return fail(e, values);
  }
}
export async function getStatusTransitions(
  signal: AbortSignal,
): Promise<StatusTransition[]> {
  try {
    return statusTransitionsFromDto(
      (
        await httpClient.get<StatusTransitionsResponseDTO>(
          `${root}/transitions`,
          { signal },
        )
      ).data,
    );
  } catch (e: unknown) {
    return fail(e);
  }
}
