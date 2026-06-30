import { httpClient } from "@/app/providers/http";
import type {
  CreateWorkflowApplicationRequestDto,
  WorkflowApplicationListResponseDto,
  WorkflowApplicationResponseDto,
} from "@/modules/workflow/applications/api/workflow-application.dto.ts";

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

export async function createWorkflowApplication(
  payload: CreateWorkflowApplicationRequestDto,
): Promise<WorkflowApplicationResponseDto> {
  const response = await httpClient.post<WorkflowApplicationResponseDto>(
    "/console/workflows",
    payload,
  );

  return response.data;
}
