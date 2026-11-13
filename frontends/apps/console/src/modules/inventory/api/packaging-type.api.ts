import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import type {
  PackagingType,
  PackagingTypeCreateValues,
  PackagingTypeChanges,
  PackagingTypeFieldErrors,
  PackagingTypesListParams,
  PackagingTypesPage,
} from "../model/packaging-type.types";
import { PackagingTypeRequestError } from "../model/packaging-type.errors";
import type {
  CreatePackagingTypeResponseDTO,
  GetPackagingTypeResponseDTO,
  PatchPackagingTypeResponseDTO,
  ListPackagingTypesResponseDTO,
} from "./packaging-type.dto";
import {
  packagingTypeFromDto,
  packagingTypeCreateToDto,
  packagingTypePatchToDto,
  packagingTypesPageFromDto,
  packagingTypesParamsToDto,
} from "./packaging-type.mapper";

function requestError(cause: unknown, fallback: string): never {
  if (isCancel(cause)) throw cause;
  const status = getApiErrorStatus(cause),
    fields: PackagingTypeFieldErrors = {};
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
      const field: unknown = issue.loc[1];
      if (field === "code" || field === "name")
        fields[field] = "Проверьте значение поля.";
      if (field === "is_active")
        fields.isActive = "Выберите активность типа тары.";
    }
  if (status === 409) fields.code = "Этот код типа тары уже занят.";
  throw new PackagingTypeRequestError(
    status === 403
      ? "Нет доступа к типам тары."
      : status === 404
        ? "Тип тары не найден."
        : getApiErrorMessage(cause, fallback),
    status,
    fields,
  );
}
export async function listPackagingTypes(
  params: PackagingTypesListParams,
  signal?: AbortSignal,
): Promise<PackagingTypesPage> {
  try {
    const { data } = await httpClient.get<ListPackagingTypesResponseDTO>(
      "/console/inventory/packaging-types",
      { params: packagingTypesParamsToDto(params), signal },
    );
    return packagingTypesPageFromDto(data);
  } catch (error: unknown) {
    return requestError(error, "Не удалось загрузить типы тары.");
  }
}
export async function getPackagingType(
  id: string,
  signal?: AbortSignal,
): Promise<PackagingType> {
  try {
    const { data } = await httpClient.get<GetPackagingTypeResponseDTO>(
      `/console/inventory/packaging-types/${encodeURIComponent(id)}`,
      { signal },
    );
    return packagingTypeFromDto(data);
  } catch (error: unknown) {
    return requestError(error, "Не удалось загрузить тип тары.");
  }
}
export async function createPackagingType(
  values: PackagingTypeCreateValues,
  signal?: AbortSignal,
): Promise<PackagingType> {
  try {
    const { data } = await httpClient.post<CreatePackagingTypeResponseDTO>(
      "/console/inventory/packaging-types",
      packagingTypeCreateToDto(values),
      { signal },
    );
    return packagingTypeFromDto(data);
  } catch (error: unknown) {
    return requestError(error, "Не удалось создать тип тары.");
  }
}
export async function patchPackagingType(
  id: string,
  values: PackagingTypeChanges,
  signal?: AbortSignal,
): Promise<PackagingType> {
  try {
    const { data } = await httpClient.patch<PatchPackagingTypeResponseDTO>(
      `/console/inventory/packaging-types/${encodeURIComponent(id)}`,
      packagingTypePatchToDto(values),
      { signal },
    );
    return packagingTypeFromDto(data);
  } catch (error: unknown) {
    return requestError(
      error,
      "Не удалось сохранить тип тары. Ваш ввод сохранён.",
    );
  }
}
