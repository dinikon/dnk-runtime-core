import { httpClient, getApiErrorMessage } from "@/app/providers/http";
import { isCancel } from "axios";
import type { GetIssueExecutionResultResponseDTO } from "./issue-execution-result.dto";
import type { IssueExecutionResult } from "../model/issue-execution-result.types";
import { issueExecutionResultFromDto } from "./issue-execution-result.mapper";
export async function getIssueExecutionResult(
  id: string,
  signal?: AbortSignal,
): Promise<IssueExecutionResult> {
  try {
    return issueExecutionResultFromDto(
      (
        await httpClient.get<GetIssueExecutionResultResponseDTO>(
          `/console/inventory/stock-executions/${encodeURIComponent(id)}/issue-result`,
          { signal },
        )
      ).data,
    );
  } catch (cause: unknown) {
    if (isCancel(cause)) throw cause;
    throw new Error(
      getApiErrorMessage(
        cause,
        "Не удалось прочитать исходный результат расхода.",
      ),
    );
  }
}
