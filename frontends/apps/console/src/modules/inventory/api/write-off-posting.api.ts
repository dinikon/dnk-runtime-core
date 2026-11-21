import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import type {
  PrepareWriteOffResponseDTO,
  ListWriteOffSourcesResponseDTO,
  ListWriteOffExecutionsResponseDTO,
  PostWriteOffResponseDTO,
} from "./write-off-posting.dto";
import {
  writeOffPreparationFromDto,
  writeOffSourcesFromDto,
  writeOffHistoryFromDto,
  writeOffExecutionToDto,
  writeOffResultFromDto,
} from "./write-off-posting.mapper";
import type {
  WriteOffPreparation,
  WriteOffSources,
  WriteOffSourceParams,
  WriteOffExecutionHistory,
  WriteOffExecutionValues,
  WriteOffPostingResult,
  WriteOffExecutionErrors,
} from "../model/write-off-posting.types";
import { WriteOffPostingRequestError } from "../model/write-off-posting.errors";
const root = "/console/inventory/stock-documents/write-offs";
function fail(cause: unknown, values?: WriteOffExecutionValues): never {
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
      : getApiErrorMessage(cause, "Не удалось выполнить действие списания.");
  const fields: WriteOffExecutionErrors = { rows: {}, lines: {} };
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
    for (const writeOff of raw) {
      if (
        typeof writeOff !== "object" ||
        writeOff === null ||
        !Array.isArray(writeOff.loc)
      )
        continue;
      const index = writeOff.loc.indexOf("lines"),
        position: unknown = writeOff.loc[index + 1];
      if (index >= 0 && typeof position === "number" && rows[position])
        fields.rows[rows[position].key] =
          typeof writeOff.msg === "string"
            ? writeOff.msg
            : "Проверьте распределение.";
    }
  throw new WriteOffPostingRequestError(
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
export async function prepareWriteOff(
  id: string,
  signal?: AbortSignal,
): Promise<WriteOffPreparation> {
  try {
    return writeOffPreparationFromDto(
      (
        await httpClient.get<PrepareWriteOffResponseDTO>(
          `${root}/${encodeURIComponent(id)}/write-off-context`,
          { signal },
        )
      ).data,
    );
  } catch (e: unknown) {
    return fail(e);
  }
}
export async function listWriteOffSources(
  id: string,
  params: WriteOffSourceParams,
  signal?: AbortSignal,
): Promise<WriteOffSources> {
  try {
    return writeOffSourcesFromDto(
      (
        await httpClient.get<ListWriteOffSourcesResponseDTO>(
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
export async function listWriteOffExecutions(
  id: string,
  offset: number,
  signal?: AbortSignal,
): Promise<WriteOffExecutionHistory> {
  try {
    return writeOffHistoryFromDto(
      (
        await httpClient.get<ListWriteOffExecutionsResponseDTO>(
          `${root}/${encodeURIComponent(id)}/executions`,
          { params: { offset, limit: 20 }, signal },
        )
      ).data,
    );
  } catch (e: unknown) {
    return fail(e);
  }
}
export async function postWriteOff(
  id: string,
  values: WriteOffExecutionValues,
  key: string,
  signal: AbortSignal,
): Promise<WriteOffPostingResult> {
  try {
    return writeOffResultFromDto(
      (
        await httpClient.post<PostWriteOffResponseDTO>(
          `${root}/${encodeURIComponent(id)}/write-off`,
          writeOffExecutionToDto(values),
          { headers: { "Idempotency-Key": key }, signal },
        )
      ).data,
    );
  } catch (e: unknown) {
    return fail(e, values);
  }
}
