import type {
  WriteOffEditValues,
  WriteOffVersionValues,
} from "../model/write-off.types";
import type {
  PatchWriteOffDocumentResponseDTO,
  ConfirmWriteOffDocumentResponseDTO,
  CancelWriteOffDocumentResponseDTO,
  ConfirmWriteOffDocumentRequestDTO,
  CancelWriteOffDocumentRequestDTO,
} from "./write-off.dto";
import { patchWriteOffToDto } from "./write-off.mapper";
import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import type {
  WriteOffDocument,
  WriteOffsPage,
  WriteOffsParams,
  WriteOffDraftValues,
  WriteOffErrors,
} from "../model/write-off.types";
import type {
  CreateWriteOffDraftResponseDTO,
  GetWriteOffDocumentResponseDTO,
  ListWriteOffDocumentsResponseDTO,
} from "./write-off.dto";
import {
  writeOffFromDto,
  writeOffsPageFromDto,
  createWriteOffToDto,
  writeOffsParamsToDto,
} from "./write-off.mapper";
import { WriteOffRequestError } from "../model/write-off.errors";
const base = "/console/inventory/stock-documents/write-offs";
function fail(
  cause: unknown,
  fallback: string,
  lineKeys: readonly string[] = [],
): never {
  if (isCancel(cause)) throw cause;
  const fields: WriteOffErrors = { lineFields: {} };
  const detail: unknown = isAxiosError(cause)
    ? cause.response?.data?.detail
    : undefined;
  if (Array.isArray(detail))
    for (const writeOff of detail) {
      if (
        typeof writeOff !== "object" ||
        writeOff === null ||
        !Array.isArray(writeOff.loc)
      )
        continue;
      const path: unknown[] = writeOff.loc;
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
              typeof writeOff.msg === "string"
                ? writeOff.msg
                : "Проверьте строку.",
          };
        } else fields.lines = "Проверьте список строк.";
      } else if (path.includes("reason"))
        fields.reason =
          typeof writeOff.msg === "string"
            ? writeOff.msg
            : "Укажите причину списания.";
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
  throw new WriteOffRequestError(
    message,
    getApiErrorStatus(cause) ?? undefined,
    fields,
    conflict,
  );
}
export async function listWriteOffs(
  params: WriteOffsParams,
  signal?: AbortSignal,
): Promise<WriteOffsPage> {
  try {
    return writeOffsPageFromDto(
      (
        await httpClient.get<ListWriteOffDocumentsResponseDTO>(base, {
          params: writeOffsParamsToDto(params),
          signal,
        })
      ).data,
    );
  } catch (cause: unknown) {
    return fail(cause, "Не удалось загрузить списания.");
  }
}
export async function getWriteOff(
  id: string,
  signal?: AbortSignal,
): Promise<WriteOffDocument> {
  try {
    return writeOffFromDto(
      (
        await httpClient.get<GetWriteOffDocumentResponseDTO>(
          `${base}/${encodeURIComponent(id)}`,
          { signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(cause, "Не удалось загрузить списание.");
  }
}
export async function createWriteOff(
  values: WriteOffDraftValues,
  key: string,
  signal: AbortSignal,
): Promise<WriteOffDocument> {
  try {
    return writeOffFromDto(
      (
        await httpClient.post<CreateWriteOffDraftResponseDTO>(
          base,
          createWriteOffToDto(values),
          { headers: { "Idempotency-Key": key }, signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(
      cause,
      "Не удалось создать списание. Введённые данные сохранены.",
      values.lines.map((l) => l.key),
    );
  }
}

export async function patchWriteOff(
  id: string,
  values: WriteOffEditValues,
  signal: AbortSignal,
): Promise<WriteOffDocument> {
  try {
    return writeOffFromDto(
      (
        await httpClient.patch<PatchWriteOffDocumentResponseDTO>(
          `${base}/${encodeURIComponent(id)}`,
          patchWriteOffToDto(values),
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
export async function confirmWriteOff(
  id: string,
  values: WriteOffVersionValues,
  signal: AbortSignal,
): Promise<WriteOffDocument> {
  const payload: ConfirmWriteOffDocumentRequestDTO = {
    expected_version: values.expectedVersion,
  };
  try {
    return writeOffFromDto(
      (
        await httpClient.post<ConfirmWriteOffDocumentResponseDTO>(
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
export async function cancelWriteOff(
  id: string,
  values: WriteOffVersionValues,
  signal: AbortSignal,
): Promise<WriteOffDocument> {
  const payload: CancelWriteOffDocumentRequestDTO = {
    expected_version: values.expectedVersion,
  };
  try {
    return writeOffFromDto(
      (
        await httpClient.post<CancelWriteOffDocumentResponseDTO>(
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
