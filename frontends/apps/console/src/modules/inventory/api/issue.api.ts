import type { IssueEditValues, IssueVersionValues } from "../model/issue.types";
import type {
  PatchIssueDocumentResponseDTO,
  ConfirmIssueDocumentResponseDTO,
  CancelIssueDocumentResponseDTO,
  ConfirmIssueDocumentRequestDTO,
  CancelIssueDocumentRequestDTO,
} from "./issue.dto";
import { patchIssueToDto } from "./issue.mapper";
import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import type {
  IssueDocument,
  IssuesPage,
  IssuesParams,
  IssueDraftValues,
  IssueErrors,
} from "../model/issue.types";
import type {
  CreateIssueDraftResponseDTO,
  GetIssueDocumentResponseDTO,
  ListIssueDocumentsResponseDTO,
} from "./issue.dto";
import {
  issueFromDto,
  issuesPageFromDto,
  createIssueToDto,
  issuesParamsToDto,
} from "./issue.mapper";
import { IssueRequestError } from "../model/issue.errors";
const base = "/console/inventory/stock-documents/issues";
function fail(
  cause: unknown,
  fallback: string,
  lineKeys: readonly string[] = [],
): never {
  if (isCancel(cause)) throw cause;
  const fields: IssueErrors = { lineFields: {} };
  const detail: unknown = isAxiosError(cause)
    ? cause.response?.data?.detail
    : undefined;
  if (Array.isArray(detail))
    for (const issue of detail) {
      if (
        typeof issue !== "object" ||
        issue === null ||
        !Array.isArray(issue.loc)
      )
        continue;
      const path: unknown[] = issue.loc;
      const line = path.indexOf("lines");
      if (line >= 0) {
        const index = path[line + 1];
        if (typeof index === "number" && lineKeys[index]) {
          const name = path[line + 2];
          const field =
            name === "inventory_item_id"
              ? "inventoryItemId"
              : name === "quantity"
                ? "quantity"
                : name === "uom"
                  ? "uom"
                  : "error";
          fields.lineFields[lineKeys[index]] = {
            ...fields.lineFields[lineKeys[index]],
            [field]:
              typeof issue.msg === "string" ? issue.msg : "Проверьте строку.",
          };
        } else fields.lines = "Проверьте список строк.";
      } else if (path.includes("warehouse_id"))
        fields.warehouseId = "Выберите склад.";
      else if (path.includes("owner_id"))
        fields.ownerId = "Выберите компанию-владельца.";
    }
  const metadata =
    typeof detail === "object" && detail !== null && !Array.isArray(detail)
      ? detail
      : undefined;
  const message =
    metadata && "message" in metadata && typeof metadata.message === "string"
      ? metadata.message
      : getApiErrorMessage(cause, fallback);
  const conflict =
    metadata && "code" in metadata && typeof metadata.code === "string"
      ? {
          code: metadata.code,
          expectedVersion:
            "expected_version" in metadata &&
            typeof metadata.expected_version === "number"
              ? metadata.expected_version
              : undefined,
          actualVersion:
            "actual_version" in metadata &&
            typeof metadata.actual_version === "number"
              ? metadata.actual_version
              : undefined,
        }
      : undefined;
  throw new IssueRequestError(
    message,
    getApiErrorStatus(cause) ?? undefined,
    fields,
    conflict,
  );
}
export async function listIssues(
  params: IssuesParams,
  signal?: AbortSignal,
): Promise<IssuesPage> {
  try {
    return issuesPageFromDto(
      (
        await httpClient.get<ListIssueDocumentsResponseDTO>(base, {
          params: issuesParamsToDto(params),
          signal,
        })
      ).data,
    );
  } catch (cause: unknown) {
    return fail(cause, "Не удалось загрузить расхода.");
  }
}
export async function getIssue(
  id: string,
  signal?: AbortSignal,
): Promise<IssueDocument> {
  try {
    return issueFromDto(
      (
        await httpClient.get<GetIssueDocumentResponseDTO>(
          `${base}/${encodeURIComponent(id)}`,
          { signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(cause, "Не удалось загрузить расход.");
  }
}
export async function createIssue(
  values: IssueDraftValues,
  key: string,
  signal: AbortSignal,
): Promise<IssueDocument> {
  try {
    return issueFromDto(
      (
        await httpClient.post<CreateIssueDraftResponseDTO>(
          base,
          createIssueToDto(values),
          { headers: { "Idempotency-Key": key }, signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(
      cause,
      "Не удалось создать расход. Введённые данные сохранены.",
      values.lines.map((l) => l.key),
    );
  }
}

export async function patchIssue(
  id: string,
  values: IssueEditValues,
  signal: AbortSignal,
): Promise<IssueDocument> {
  try {
    return issueFromDto(
      (
        await httpClient.patch<PatchIssueDocumentResponseDTO>(
          `${base}/${encodeURIComponent(id)}`,
          patchIssueToDto(values),
          { signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(
      cause,
      "Не удалось сохранить план. Введённые данные сохранены.",
      values.lines.map((line) => line.key),
    );
  }
}
export async function confirmIssue(
  id: string,
  values: IssueVersionValues,
  signal: AbortSignal,
): Promise<IssueDocument> {
  const payload: ConfirmIssueDocumentRequestDTO = {
    expected_version: values.expectedVersion,
  };
  try {
    return issueFromDto(
      (
        await httpClient.post<ConfirmIssueDocumentResponseDTO>(
          `${base}/${encodeURIComponent(id)}/confirm`,
          payload,
          { signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(cause, "Не удалось подтвердить план.");
  }
}
export async function cancelIssue(
  id: string,
  values: IssueVersionValues,
  signal: AbortSignal,
): Promise<IssueDocument> {
  const payload: CancelIssueDocumentRequestDTO = {
    expected_version: values.expectedVersion,
  };
  try {
    return issueFromDto(
      (
        await httpClient.post<CancelIssueDocumentResponseDTO>(
          `${base}/${encodeURIComponent(id)}/cancel`,
          payload,
          { signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(cause, "Не удалось отменить документ.");
  }
}
