import { useMutation, useQueryClient } from "@tanstack/vue-query";

import { createWorkflowApplication } from "@/modules/workflow/applications/api/workflow-application.api.ts";
import { mapCreateWorkflowApplicationPayload } from "@/modules/workflow/applications/model/workflow-application.mapper.ts";
import { workflowApplicationQueryKeys } from "@/modules/workflow/applications/model/workflow-application.query-keys.ts";
import type { CreateWorkflowApplicationPayload } from "@/modules/workflow/applications/model/workflow-application.types.ts";

export function useCreateWorkflowApplication() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateWorkflowApplicationPayload) => {
      return createWorkflowApplication(
        mapCreateWorkflowApplicationPayload(payload),
      );
    },

    onSuccess: async (): Promise<void> => {
      await queryClient.invalidateQueries({
        queryKey: workflowApplicationQueryKeys.applications(),
      });
    },
  });
}
