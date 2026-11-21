import type {
  ReturnEditValues,
  ReturnVersionValues,
} from "../model/return.types";
import type {
  PatchReturnDocumentResponseDTO,
  ConfirmReturnDocumentResponseDTO,
  CancelReturnDocumentResponseDTO,
  ConfirmReturnDocumentRequestDTO,
  CancelReturnDocumentRequestDTO,
} from "./return.dto";
import { patchReturnToDto } from "./return.mapper";
import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import type {
  ReturnDocument,
  ReturnsPage,
  ReturnsParams,
  ReturnDraftValues,
  ReturnErrors,
} from "../model/return.types";
import type {
  CreateReturnDraftResponseDTO,
  GetReturnDocumentResponseDTO,
  ListReturnDocumentsResponseDTO,
} from "./return.dto";
import {
  returnFromDto,
  returnsPageFromDto,
  createReturnToDto,
  returnsParamsToDto,
} from "./return.mapper";
import { ReturnRequestError } from "../model/return.errors";
const base = "/console/inventory/stock-documents/returns";
function fail(
  cause: unknown,
  fallback: string,
  lineKeys: readonly string[] = [],
): never {
  if (isCancel(cause)) throw cause;
  const fields: ReturnErrors = { lineFields: {} };
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
      } else if (path.includes("reason"))
        fields.reason =
          typeof issue.msg === "string"
            ? issue.msg
            : "Укажите причину возврата.";
      else if (path.includes("warehouse_id"))
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
  throw new ReturnRequestError(
    message,
    getApiErrorStatus(cause) ?? undefined,
    fields,
    conflict,
  );
}
export async function listReturns(
  params: ReturnsParams,
  signal?: AbortSignal,
): Promise<ReturnsPage> {
  try {
    return returnsPageFromDto(
      (
        await httpClient.get<ListReturnDocumentsResponseDTO>(base, {
          params: returnsParamsToDto(params),
          signal,
        })
      ).data,
    );
  } catch (cause: unknown) {
    return fail(cause, "Не удалось загрузить возврата.");
  }
}
export async function getReturn(
  id: string,
  signal?: AbortSignal,
): Promise<ReturnDocument> {
  try {
    return returnFromDto(
      (
        await httpClient.get<GetReturnDocumentResponseDTO>(
          `${base}/${encodeURIComponent(id)}`,
          { signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(cause, "Не удалось загрузить возврат.");
  }
}
export async function createReturn(
  values: ReturnDraftValues,
  key: string,
  signal: AbortSignal,
): Promise<ReturnDocument> {
  try {
    return returnFromDto(
      (
        await httpClient.post<CreateReturnDraftResponseDTO>(
          base,
          createReturnToDto(values),
          { headers: { "Idempotency-Key": key }, signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(
      cause,
      "Не удалось создать возврат. Введённые данные сохранены.",
      values.lines.map((l) => l.key),
    );
  }
}

export async function patchReturn(
  id: string,
  values: ReturnEditValues,
  signal: AbortSignal,
): Promise<ReturnDocument> {
  try {
    return returnFromDto(
      (
        await httpClient.patch<PatchReturnDocumentResponseDTO>(
          `${base}/${encodeURIComponent(id)}`,
          patchReturnToDto(values),
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
export async function confirmReturn(
  id: string,
  values: ReturnVersionValues,
  signal: AbortSignal,
): Promise<ReturnDocument> {
  const payload: ConfirmReturnDocumentRequestDTO = {
    expected_version: values.expectedVersion,
  };
  try {
    return returnFromDto(
      (
        await httpClient.post<ConfirmReturnDocumentResponseDTO>(
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
export async function cancelReturn(
  id: string,
  values: ReturnVersionValues,
  signal: AbortSignal,
): Promise<ReturnDocument> {
  const payload: CancelReturnDocumentRequestDTO = {
    expected_version: values.expectedVersion,
  };
  try {
    return returnFromDto(
      (
        await httpClient.post<CancelReturnDocumentResponseDTO>(
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
