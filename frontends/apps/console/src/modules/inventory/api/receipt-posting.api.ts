import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import type {
  PostReceiptResponseDTO,
  GetStockExecutionResponseDTO,
  GetStockPostingResponseDTO,
  PrepareReceiptResponseDTO,
  ListReceiptReferencesResponseDTO,
  ListReceiptExecutionsResponseDTO,
} from "./receipt-posting.dto";
import type {
  ReceiptPostingResult,
  ReceiptPreparation,
  ReceiptIntakeValues,
  ReceiptIntakeErrors,
  ReceiptReferencesParams,
  IntakeReferencesPage,
  ReceiptExecutionHistory,
} from "../model/receipt-posting.types";
import {
  postingResultFromDto,
  preparationFromDto,
  intakeToDto,
  referencesFromDto,
  executionHistoryFromDto,
} from "./receipt-posting.mapper";
import { ReceiptPostingRequestError } from "../model/receipt-posting.errors";
const root = "/console/inventory";
function fail(
  cause: unknown,
  fallback: string,
  values?: ReceiptIntakeValues,
): never {
  if (isCancel(cause)) throw cause;
  const raw: unknown = isAxiosError(cause)
    ? cause.response?.data?.detail
    : undefined;
  const metadata =
    typeof raw === "object" && raw !== null && !Array.isArray(raw)
      ? raw
      : undefined;
  const message =
    metadata && "message" in metadata && typeof metadata.message === "string"
      ? metadata.message
      : getApiErrorMessage(cause, fallback);
  const code =
    metadata && "code" in metadata && typeof metadata.code === "string"
      ? metadata.code
      : undefined;
  const actual =
    metadata &&
    "actual_version" in metadata &&
    typeof metadata.actual_version === "number"
      ? metadata.actual_version
      : undefined;
  const fields: ReceiptIntakeErrors = { rows: {} };
  if (Array.isArray(raw) && values)
    for (const issue of raw) {
      if (
        typeof issue !== "object" ||
        issue === null ||
        !Array.isArray(issue.loc)
      )
        continue;
      const index = issue.loc.indexOf("lines"),
        position: unknown = issue.loc[index + 1];
      if (index >= 0 && typeof position === "number" && values.rows[position])
        fields.rows[values.rows[position].key] =
          typeof issue.msg === "string"
            ? issue.msg
            : "Проверьте фактическую строку.";
    }
  throw new ReceiptPostingRequestError(
    message,
    getApiErrorStatus(cause) ?? undefined,
    code,
    actual,
    fields,
  );
}
export async function prepareReceipt(
  id: string,
  signal?: AbortSignal,
): Promise<ReceiptPreparation> {
  try {
    return preparationFromDto(
      (
        await httpClient.get<PrepareReceiptResponseDTO>(
          `${root}/stock-documents/${encodeURIComponent(id)}/receipt-context`,
          { signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(cause, "Не удалось подготовить приёмку.");
  }
}
export async function postReceipt(
  id: string,
  values: ReceiptIntakeValues,
  key: string,
  signal: AbortSignal,
): Promise<ReceiptPostingResult> {
  try {
    return postingResultFromDto(
      (
        await httpClient.post<PostReceiptResponseDTO>(
          `${root}/stock-documents/${encodeURIComponent(id)}/receive`,
          intakeToDto(values),
          { headers: { "Idempotency-Key": key }, signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(
      cause,
      "Не удалось провести приёмку. Введённый факт сохранён.",
      values,
    );
  }
}
export async function getReceiptExecution(
  id: string,
  signal?: AbortSignal,
): Promise<ReceiptPostingResult> {
  try {
    return postingResultFromDto(
      (
        await httpClient.get<GetStockExecutionResponseDTO>(
          `${root}/stock-executions/${encodeURIComponent(id)}`,
          { signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(cause, "Не удалось прочитать исполнение.");
  }
}
export async function getReceiptPosting(
  id: string,
  signal?: AbortSignal,
): Promise<ReceiptPostingResult> {
  try {
    return postingResultFromDto(
      (
        await httpClient.get<GetStockPostingResponseDTO>(
          `${root}/stock-postings/${encodeURIComponent(id)}`,
          { signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(cause, "Не удалось прочитать проводку.");
  }
}
export async function findReceiptReferences(
  id: string,
  params: ReceiptReferencesParams,
  signal?: AbortSignal,
): Promise<IntakeReferencesPage> {
  try {
    return referencesFromDto(
      (
        await httpClient.get<ListReceiptReferencesResponseDTO>(
          `${root}/stock-documents/${encodeURIComponent(id)}/receipt-references`,
          {
            params: {
              kind: params.kind,
              document_line_id: params.documentLineId,
              lot_id: params.lotId,
              search: params.search.trim() || undefined,
              offset: params.offset,
              limit: params.limit,
            },
            signal,
          },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(cause, "Не удалось загрузить варианты выбора.");
  }
}
export async function listReceiptExecutions(
  id: string,
  offset: number,
  signal?: AbortSignal,
): Promise<ReceiptExecutionHistory> {
  try {
    return executionHistoryFromDto(
      (
        await httpClient.get<ListReceiptExecutionsResponseDTO>(
          `${root}/stock-documents/${encodeURIComponent(id)}/executions`,
          { params: { offset, limit: 20 }, signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(cause, "Не удалось загрузить историю приёмок.");
  }
}
