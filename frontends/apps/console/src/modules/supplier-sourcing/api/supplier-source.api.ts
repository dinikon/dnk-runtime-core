import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import { SupplierSourceRequestError } from "../model/supplier-source.errors";
import type {
  SourceValues,
  SourceChanges,
  SupplierSource,
  SourcesPage,
  SourcesParams,
  SourceFieldErrors,
} from "../model/supplier-source.types";
import type {
  CreateSupplierSourceResponseDTO,
  GetSupplierSourceResponseDTO,
  PatchSupplierSourceResponseDTO,
  ListSupplierSourcesResponseDTO,
} from "./supplier-source.dto";
import {
  sourceFromDto,
  sourceCreateToDto,
  sourcePatchToDto,
  sourcesPageFromDto,
  sourcesParamsToDto,
} from "./supplier-source.mapper";
const base = "/console/supplier-sourcing/sources";
function requestError(cause: unknown, fallback: string): never {
  if (isCancel(cause)) throw cause;
  const fields: SourceFieldErrors = {};
  const detail: unknown = isAxiosError(cause)
    ? cause.response?.data?.detail
    : undefined;
  const names: Record<string, keyof SourceValues> = {
    supplier_model_key: "supplierModelKey",
    supplier_id: "supplierId",
    name: "name",
    external_warehouse_code: "externalWarehouseCode",
    fulfillment_modes: "fulfillmentModes",
    default_lead_time_seconds: "leadTimeSeconds",
    is_active: "isActive",
    ttl_seconds: "ttlSeconds",
    stale_behavior: "staleBehavior",
    missing_sku_behavior: "missingSkuBehavior",
  };
  if (Array.isArray(detail))
    for (const issue of detail) {
      if (
        typeof issue !== "object" ||
        issue === null ||
        !Array.isArray(issue.loc)
      )
        continue;
      const path = issue.loc.filter(
        (part: unknown): part is string => typeof part === "string",
      );
      const field = names[path.at(-1) ?? ""];
      if (field) fields[field] = "Проверьте значение поля.";
    }
  throw new SupplierSourceRequestError(
    getApiErrorMessage(cause, fallback),
    getApiErrorStatus(cause) ?? undefined,
    fields,
  );
}
export async function listSupplierSources(
  params: SourcesParams,
  signal?: AbortSignal,
): Promise<SourcesPage> {
  try {
    const { data } = await httpClient.get<ListSupplierSourcesResponseDTO>(
      base,
      { params: sourcesParamsToDto(params), signal },
    );
    return sourcesPageFromDto(data);
  } catch (error: unknown) {
    return requestError(error, "Не удалось загрузить источники.");
  }
}
export async function getSupplierSource(
  id: string,
  signal?: AbortSignal,
): Promise<SupplierSource> {
  try {
    const { data } = await httpClient.get<GetSupplierSourceResponseDTO>(
      `${base}/${encodeURIComponent(id)}`,
      { signal },
    );
    return sourceFromDto(data);
  } catch (error: unknown) {
    return requestError(error, "Не удалось загрузить источник.");
  }
}
export async function createSupplierSource(
  values: SourceValues,
  signal: AbortSignal,
): Promise<SupplierSource> {
  try {
    const { data } = await httpClient.post<CreateSupplierSourceResponseDTO>(
      base,
      sourceCreateToDto(values),
      { signal },
    );
    return sourceFromDto(data);
  } catch (error: unknown) {
    return requestError(error, "Не удалось создать источник.");
  }
}
export async function patchSupplierSource(
  id: string,
  changes: SourceChanges,
  signal: AbortSignal,
): Promise<SupplierSource> {
  try {
    const { data } = await httpClient.patch<PatchSupplierSourceResponseDTO>(
      `${base}/${encodeURIComponent(id)}`,
      sourcePatchToDto(changes),
      { signal },
    );
    return sourceFromDto(data);
  } catch (error: unknown) {
    return requestError(
      error,
      "Не удалось сохранить источник. Ваш ввод сохранён.",
    );
  }
}
