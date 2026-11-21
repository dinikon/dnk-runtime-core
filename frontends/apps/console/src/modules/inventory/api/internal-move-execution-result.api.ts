import { httpClient, getApiErrorMessage } from "@/app/providers/http";
import { isCancel } from "axios";
import type { GetInternalMoveExecutionResultResponseDTO } from "./internal-move-execution-result.dto";
import type { InternalMoveExecutionResult } from "../model/internal-move-execution-result.types";
import { internalMoveExecutionResultFromDto } from "./internal-move-execution-result.mapper";
export async function getInternalMoveExecutionResult(
  id: string,
  signal?: AbortSignal,
): Promise<InternalMoveExecutionResult> {
  try {
    return internalMoveExecutionResultFromDto(
      (
        await httpClient.get<GetInternalMoveExecutionResultResponseDTO>(
          `/console/inventory/stock-executions/${encodeURIComponent(id)}/internal-move-result`,
          { signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    if (isCancel(cause)) throw cause;
    throw new Error(
      getApiErrorMessage(
        cause,
        "Не удалось прочитать исходный результат перемещения.",
      ),
    );
  }
}
