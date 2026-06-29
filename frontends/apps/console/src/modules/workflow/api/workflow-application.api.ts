import { httpClient } from "@/app/providers/http";
import type { WorkflowApplicationListResponseDto } from "@/modules/workflow/api/workflow-application.dto.ts";
import type {
  WorkflowApplicationListResponse,
  WorkflowCursor,
} from "@/modules/workflow/model/workflow-application.types.ts";
import { mapWorkflowApplicationList } from "@/modules/workflow/api/workflow-application.mapper.ts";

interface ListWorkflowApplicationsParams {
  limit: number;
  cursor: WorkflowCursor;
}

export async function listWorkflowApplications(
  params: ListWorkflowApplicationsParams,
): Promise<WorkflowApplicationListResponse> {
  const response = await httpClient.get<WorkflowApplicationListResponseDto>(
    "/console/workflows",
    {
      params: {
        limit: params.limit,
        cursor: params.cursor ?? undefined,
      },
    },
  );

  return mapWorkflowApplicationList(response.data);
}
