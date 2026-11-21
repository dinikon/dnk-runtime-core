import type {
  StatusChangeEditValues,
  StatusChangeVersionValues,
} from "../model/status-change.types";
import type {
  PatchStatusChangeDocumentResponseDTO,
  ConfirmStatusChangeDocumentResponseDTO,
  CancelStatusChangeDocumentResponseDTO,
  ConfirmStatusChangeDocumentRequestDTO,
  CancelStatusChangeDocumentRequestDTO,
} from "./status-change.dto";
import { patchStatusChangeToDto } from "./status-change.mapper";
import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import type {
  StatusChangeDocument,
  StatusChangesPage,
  StatusChangesParams,
  StatusChangeDraftValues,
  StatusChangeErrors,
} from "../model/status-change.types";
import type {
  CreateStatusChangeDraftResponseDTO,
  GetStatusChangeDocumentResponseDTO,
  ListStatusChangeDocumentsResponseDTO,
} from "./status-change.dto";
import {
  statusChangeFromDto,
  statusChangesPageFromDto,
  createStatusChangeToDto,
  statusChangesParamsToDto,
} from "./status-change.mapper";
import { StatusChangeRequestError } from "../model/status-change.errors";
const base = "/console/inventory/stock-documents/status-changes";
function fail(
  cause: unknown,
  fallback: string,
  lineKeys: readonly string[] = [],
): never {
  if (isCancel(cause)) throw cause;
  const fields: StatusChangeErrors = { lineFields: {} };
  const detail: unknown = isAxiosError(cause)
    ? cause.response?.data?.detail
    : undefined;
  if (Array.isArray(detail))
    for (const statusChange of detail) {
      if (
        typeof statusChange !== "object" ||
        statusChange === null ||
        !Array.isArray(statusChange.loc)
      )
        continue;
      const path: unknown[] = statusChange.loc;
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
              typeof statusChange.msg === "string"
                ? statusChange.msg
                : "Проверьте строку.",
          };
        } else fields.lines = "Проверьте список строк.";
      } else if (path.includes("reason"))
        fields.reason =
          typeof statusChange.msg === "string"
            ? statusChange.msg
            : "Укажите причину изменения состояния.";
      else if (path.includes("warehouse_id"))
        fields.warehouseId = "Выберите склад.";
      else if (path.includes("target_status"))
        fields.targetStatus = "Выберите новое состояние.";
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
  throw new StatusChangeRequestError(
    message,
    getApiErrorStatus(cause) ?? undefined,
    fields,
    conflict,
  );
}
export async function listStatusChanges(
  params: StatusChangesParams,
  signal?: AbortSignal,
): Promise<StatusChangesPage> {
  try {
    return statusChangesPageFromDto(
      (
        await httpClient.get<ListStatusChangeDocumentsResponseDTO>(base, {
          params: statusChangesParamsToDto(params),
          signal,
        })
      ).data,
    );
  } catch (cause: unknown) {
    return fail(cause, "Не удалось загрузить изменения состояния.");
  }
}
export async function getStatusChange(
  id: string,
  signal?: AbortSignal,
): Promise<StatusChangeDocument> {
  try {
    return statusChangeFromDto(
      (
        await httpClient.get<GetStatusChangeDocumentResponseDTO>(
          `${base}/${encodeURIComponent(id)}`,
          { signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(cause, "Не удалось загрузить изменение состояния.");
  }
}
export async function createStatusChange(
  values: StatusChangeDraftValues,
  key: string,
  signal: AbortSignal,
): Promise<StatusChangeDocument> {
  try {
    return statusChangeFromDto(
      (
        await httpClient.post<CreateStatusChangeDraftResponseDTO>(
          base,
          createStatusChangeToDto(values),
          { headers: { "Idempotency-Key": key }, signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(
      cause,
      "Не удалось создать изменение состояния. Введённые данные сохранены.",
      values.lines.map((l) => l.key),
    );
  }
}

export async function patchStatusChange(
  id: string,
  values: StatusChangeEditValues,
  signal: AbortSignal,
): Promise<StatusChangeDocument> {
  try {
    return statusChangeFromDto(
      (
        await httpClient.patch<PatchStatusChangeDocumentResponseDTO>(
          `${base}/${encodeURIComponent(id)}`,
          patchStatusChangeToDto(values),
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
export async function confirmStatusChange(
  id: string,
  values: StatusChangeVersionValues,
  signal: AbortSignal,
): Promise<StatusChangeDocument> {
  const payload: ConfirmStatusChangeDocumentRequestDTO = {
    expected_version: values.expectedVersion,
  };
  try {
    return statusChangeFromDto(
      (
        await httpClient.post<ConfirmStatusChangeDocumentResponseDTO>(
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
export async function cancelStatusChange(
  id: string,
  values: StatusChangeVersionValues,
  signal: AbortSignal,
): Promise<StatusChangeDocument> {
  const payload: CancelStatusChangeDocumentRequestDTO = {
    expected_version: values.expectedVersion,
  };
  try {
    return statusChangeFromDto(
      (
        await httpClient.post<CancelStatusChangeDocumentResponseDTO>(
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
