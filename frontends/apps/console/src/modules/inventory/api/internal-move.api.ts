import type {
  InternalMoveEditValues,
  InternalMoveVersionValues,
} from "../model/internal-move.types";
import type {
  PatchInternalMoveDocumentResponseDTO,
  ConfirmInternalMoveDocumentResponseDTO,
  CancelInternalMoveDocumentResponseDTO,
  ConfirmInternalMoveDocumentRequestDTO,
  CancelInternalMoveDocumentRequestDTO,
} from "./internal-move.dto";
import { patchInternalMoveToDto } from "./internal-move.mapper";
import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import type {
  InternalMoveDocument,
  InternalMovesPage,
  InternalMovesParams,
  InternalMoveDraftValues,
  InternalMoveErrors,
} from "../model/internal-move.types";
import type {
  CreateInternalMoveDraftResponseDTO,
  GetInternalMoveDocumentResponseDTO,
  ListInternalMoveDocumentsResponseDTO,
} from "./internal-move.dto";
import {
  internalMoveFromDto,
  internalMovesPageFromDto,
  createInternalMoveToDto,
  internalMovesParamsToDto,
} from "./internal-move.mapper";
import { InternalMoveRequestError } from "../model/internal-move.errors";
const base = "/console/inventory/stock-documents/internal-moves";
function fail(
  cause: unknown,
  fallback: string,
  lineKeys: readonly string[] = [],
): never {
  if (isCancel(cause)) throw cause;
  const fields: InternalMoveErrors = { lineFields: {} };
  const detail: unknown = isAxiosError(cause)
    ? cause.response?.data?.detail
    : undefined;
  if (Array.isArray(detail))
    for (const internalMove of detail) {
      if (
        typeof internalMove !== "object" ||
        internalMove === null ||
        !Array.isArray(internalMove.loc)
      )
        continue;
      const path: unknown[] = internalMove.loc;
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
              typeof internalMove.msg === "string"
                ? internalMove.msg
                : "Проверьте строку.",
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
  throw new InternalMoveRequestError(
    message,
    getApiErrorStatus(cause) ?? undefined,
    fields,
    conflict,
  );
}
export async function listInternalMoves(
  params: InternalMovesParams,
  signal?: AbortSignal,
): Promise<InternalMovesPage> {
  try {
    return internalMovesPageFromDto(
      (
        await httpClient.get<ListInternalMoveDocumentsResponseDTO>(base, {
          params: internalMovesParamsToDto(params),
          signal,
        })
      ).data,
    );
  } catch (cause: unknown) {
    return fail(cause, "Не удалось загрузить перемещения.");
  }
}
export async function getInternalMove(
  id: string,
  signal?: AbortSignal,
): Promise<InternalMoveDocument> {
  try {
    return internalMoveFromDto(
      (
        await httpClient.get<GetInternalMoveDocumentResponseDTO>(
          `${base}/${encodeURIComponent(id)}`,
          { signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(cause, "Не удалось загрузить перемещение.");
  }
}
export async function createInternalMove(
  values: InternalMoveDraftValues,
  key: string,
  signal: AbortSignal,
): Promise<InternalMoveDocument> {
  try {
    return internalMoveFromDto(
      (
        await httpClient.post<CreateInternalMoveDraftResponseDTO>(
          base,
          createInternalMoveToDto(values),
          { headers: { "Idempotency-Key": key }, signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(
      cause,
      "Не удалось создать перемещение. Введённые данные сохранены.",
      values.lines.map((l) => l.key),
    );
  }
}

export async function patchInternalMove(
  id: string,
  values: InternalMoveEditValues,
  signal: AbortSignal,
): Promise<InternalMoveDocument> {
  try {
    return internalMoveFromDto(
      (
        await httpClient.patch<PatchInternalMoveDocumentResponseDTO>(
          `${base}/${encodeURIComponent(id)}`,
          patchInternalMoveToDto(values),
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
export async function confirmInternalMove(
  id: string,
  values: InternalMoveVersionValues,
  signal: AbortSignal,
): Promise<InternalMoveDocument> {
  const payload: ConfirmInternalMoveDocumentRequestDTO = {
    expected_version: values.expectedVersion,
  };
  try {
    return internalMoveFromDto(
      (
        await httpClient.post<ConfirmInternalMoveDocumentResponseDTO>(
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
export async function cancelInternalMove(
  id: string,
  values: InternalMoveVersionValues,
  signal: AbortSignal,
): Promise<InternalMoveDocument> {
  const payload: CancelInternalMoveDocumentRequestDTO = {
    expected_version: values.expectedVersion,
  };
  try {
    return internalMoveFromDto(
      (
        await httpClient.post<CancelInternalMoveDocumentResponseDTO>(
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
