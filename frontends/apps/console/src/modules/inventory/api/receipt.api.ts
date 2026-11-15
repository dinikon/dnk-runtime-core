import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import type {
  ReceiptDocument,
  ReceiptsPage,
  ReceiptsParams,
  ReceiptDraftValues,
  ReceiptErrors,
} from "../model/receipt.types";
import type {
  CreateReceiptDraftResponseDTO,
  GetReceiptDocumentResponseDTO,
  ListReceiptDocumentsResponseDTO,
} from "./receipt.dto";
import {
  receiptFromDto,
  receiptsPageFromDto,
  createReceiptToDto,
  receiptsParamsToDto,
} from "./receipt.mapper";
import { ReceiptRequestError } from "../model/receipt.errors";
const base = "/console/inventory/stock-documents";
function fail(
  cause: unknown,
  fallback: string,
  lineKeys: readonly string[] = [],
): never {
  if (isCancel(cause)) throw cause;
  const fields: ReceiptErrors = { lineFields: {} };
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
  throw new ReceiptRequestError(
    getApiErrorMessage(cause, fallback),
    getApiErrorStatus(cause) ?? undefined,
    fields,
  );
}
export async function listReceipts(
  params: ReceiptsParams,
  signal?: AbortSignal,
): Promise<ReceiptsPage> {
  try {
    return receiptsPageFromDto(
      (
        await httpClient.get<ListReceiptDocumentsResponseDTO>(base, {
          params: receiptsParamsToDto(params),
          signal,
        })
      ).data,
    );
  } catch (cause: unknown) {
    return fail(cause, "Не удалось загрузить поступления.");
  }
}
export async function getReceipt(
  id: string,
  signal?: AbortSignal,
): Promise<ReceiptDocument> {
  try {
    return receiptFromDto(
      (
        await httpClient.get<GetReceiptDocumentResponseDTO>(
          `${base}/${encodeURIComponent(id)}`,
          { signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(cause, "Не удалось загрузить поступление.");
  }
}
export async function createReceipt(
  values: ReceiptDraftValues,
  key: string,
  signal: AbortSignal,
): Promise<ReceiptDocument> {
  try {
    return receiptFromDto(
      (
        await httpClient.post<CreateReceiptDraftResponseDTO>(
          base,
          createReceiptToDto(values),
          { headers: { "Idempotency-Key": key }, signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    return fail(
      cause,
      "Не удалось создать поступление. Введённые данные сохранены.",
      values.lines.map((l) => l.key),
    );
  }
}
