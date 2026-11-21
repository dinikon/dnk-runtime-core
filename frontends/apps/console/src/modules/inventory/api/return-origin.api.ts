import { ReturnRequestError } from "../model/return.errors";
import { isAxiosError, isCancel } from "axios";
import { httpClient, getApiErrorMessage } from "@/app/providers/http";
import type { ReturnOriginResponseDTO } from "./return-origin.dto";
import type { ReturnOrigin } from "../model/return-origin.types";
import { returnOriginFromDto } from "./return-origin.mapper";
export async function getReturnOrigin(
  id: string,
  signal: AbortSignal,
): Promise<ReturnOrigin> {
  try {
    return returnOriginFromDto(
      (
        await httpClient.get<ReturnOriginResponseDTO>(
          `/console/inventory/stock-executions/${encodeURIComponent(id)}/return-context`,
          { signal },
        )
      ).data,
    );
  } catch (e: unknown) {
    if (isCancel(e)) throw e;
    throw new ReturnRequestError(
      getApiErrorMessage(e, "Не удалось загрузить основание возврата."),
      isAxiosError(e) ? e.response?.status : undefined,
    );
  }
}
