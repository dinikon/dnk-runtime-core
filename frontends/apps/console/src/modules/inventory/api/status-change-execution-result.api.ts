import { httpClient, getApiErrorMessage } from "@/app/providers/http";
import { isCancel } from "axios";
import type { GetStatusChangeExecutionResultResponseDTO } from "./status-change-execution-result.dto";
import type { StatusChangeExecutionResult } from "../model/status-change-execution-result.types";
import { statusChangeExecutionResultFromDto } from "./status-change-execution-result.mapper";
export async function getStatusChangeExecutionResult(
  id: string,
  signal?: AbortSignal,
): Promise<StatusChangeExecutionResult> {
  try {
    return statusChangeExecutionResultFromDto(
      (
        await httpClient.get<GetStatusChangeExecutionResultResponseDTO>(
          `/console/inventory/stock-executions/${encodeURIComponent(id)}/status-change-result`,
          { signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    if (isCancel(cause)) throw cause;
    throw new Error(
      getApiErrorMessage(
        cause,
        "Не удалось прочитать исходный результат изменения состояния.",
      ),
    );
  }
}
