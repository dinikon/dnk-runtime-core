import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import type {
  PrepareIssueResponseDTO,
  ListIssueSourcesResponseDTO,
  ListIssueExecutionsResponseDTO,
  PostIssueResponseDTO,
} from "./issue-posting.dto";
import {
  issuePreparationFromDto,
  issueSourcesFromDto,
  issueHistoryFromDto,
  issueExecutionToDto,
  issueResultFromDto,
} from "./issue-posting.mapper";
import type {
  IssuePreparation,
  IssueSources,
  IssueSourceParams,
  IssueExecutionHistory,
  IssueExecutionValues,
  IssuePostingResult,
  IssueExecutionErrors,
} from "../model/issue-posting.types";
import { IssuePostingRequestError } from "../model/issue-posting.errors";
const root = "/console/inventory/stock-documents/issues";
function fail(cause: unknown, values?: IssueExecutionValues): never {
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
      : getApiErrorMessage(cause, "Не удалось выполнить действие расхода.");
  const fields: IssueExecutionErrors = { rows: {}, lines: {} };
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
  throw new IssuePostingRequestError(
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
export async function prepareIssue(
  id: string,
  signal?: AbortSignal,
): Promise<IssuePreparation> {
  try {
    return issuePreparationFromDto(
      (
        await httpClient.get<PrepareIssueResponseDTO>(
          `${root}/${encodeURIComponent(id)}/issue-context`,
          { signal },
        )
      ).data,
    );
  } catch (e: unknown) {
    return fail(e);
  }
}
export async function listIssueSources(
  id: string,
  params: IssueSourceParams,
  signal?: AbortSignal,
): Promise<IssueSources> {
  try {
    return issueSourcesFromDto(
      (
        await httpClient.get<ListIssueSourcesResponseDTO>(
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
export async function listIssueExecutions(
  id: string,
  offset: number,
  signal?: AbortSignal,
): Promise<IssueExecutionHistory> {
  try {
    return issueHistoryFromDto(
      (
        await httpClient.get<ListIssueExecutionsResponseDTO>(
          `${root}/${encodeURIComponent(id)}/executions`,
          { params: { offset, limit: 20 }, signal },
        )
      ).data,
    );
  } catch (e: unknown) {
    return fail(e);
  }
}
export async function postIssue(
  id: string,
  values: IssueExecutionValues,
  key: string,
  signal: AbortSignal,
): Promise<IssuePostingResult> {
  try {
    return issueResultFromDto(
      (
        await httpClient.post<PostIssueResponseDTO>(
          `${root}/${encodeURIComponent(id)}/issue`,
          issueExecutionToDto(values),
          { headers: { "Idempotency-Key": key }, signal },
        )
      ).data,
    );
  } catch (e: unknown) {
    return fail(e, values);
  }
}
