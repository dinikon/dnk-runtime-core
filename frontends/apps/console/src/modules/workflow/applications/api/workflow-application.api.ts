import { httpClient } from "@/app/providers/http";
import type { WorkflowApplicationListResponseDto } from "@/modules/workflow/applications/api/workflow-application.dto.ts";

interface ListWorkflowApplicationsParams {
  limit: number;
  cursor: string | null;
}

export async function listWorkflowApplications(
  params: ListWorkflowApplicationsParams,
): Promise<WorkflowApplicationListResponseDto> {
  const response = await httpClient.get<WorkflowApplicationListResponseDto>(
    "/console/workflows",
    {
      params: {
        limit: params.limit,
        cursor: params.cursor ?? undefined,
      },
    },
  );

  return response.data;
}
