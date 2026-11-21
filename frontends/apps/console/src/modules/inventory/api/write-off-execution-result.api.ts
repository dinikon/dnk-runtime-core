import { httpClient, getApiErrorMessage } from "@/app/providers/http";
import { isCancel } from "axios";
import type { GetWriteOffExecutionResultResponseDTO } from "./write-off-execution-result.dto";
import type { WriteOffExecutionResult } from "../model/write-off-execution-result.types";
import { writeOffExecutionResultFromDto } from "./write-off-execution-result.mapper";
export async function getWriteOffExecutionResult(
  id: string,
  signal?: AbortSignal,
): Promise<WriteOffExecutionResult> {
  try {
    return writeOffExecutionResultFromDto(
      (
        await httpClient.get<GetWriteOffExecutionResultResponseDTO>(
          `/console/inventory/stock-executions/${encodeURIComponent(id)}/write-off-result`,
          { signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    if (isCancel(cause)) throw cause;
    throw new Error(
      getApiErrorMessage(
        cause,
        "Не удалось прочитать исходный результат списания.",
      ),
    );
  }
}
