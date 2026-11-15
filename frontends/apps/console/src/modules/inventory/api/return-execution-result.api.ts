import { httpClient, getApiErrorMessage } from "@/app/providers/http";
import { isCancel } from "axios";
import type { GetReturnExecutionResultResponseDTO } from "./return-execution-result.dto";
import type { ReturnExecutionResult } from "../model/return-execution-result.types";
import { returnExecutionResultFromDto } from "./return-execution-result.mapper";
export async function getReturnExecutionResult(
  id: string,
  signal?: AbortSignal,
): Promise<ReturnExecutionResult> {
  try {
    return returnExecutionResultFromDto(
      (
        await httpClient.get<GetReturnExecutionResultResponseDTO>(
          `/console/inventory/stock-executions/${encodeURIComponent(id)}/return-result`,
          { signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    if (isCancel(cause)) throw cause;
    throw new Error(
      getApiErrorMessage(
        cause,
        "Не удалось прочитать исходный результат возврата.",
      ),
    );
  }
}
