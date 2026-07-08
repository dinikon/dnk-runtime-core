import { useMutation, useQueryClient } from "@tanstack/vue-query";

import { updateWorkflowApplication } from "@/modules/workflow/applications/api/workflow-application.api.ts";
import { mapUpdateWorkflowApplicationPayload } from "@/modules/workflow/applications/model/workflow-application.mapper.ts";
import { workflowApplicationQueryKeys } from "@/modules/workflow/applications/model/workflow-application.query-keys.ts";
import type { UpdateWorkflowApplicationPayload } from "@/modules/workflow/applications/model/workflow-application.types.ts";

export function useUpdateWorkflowApplication() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: UpdateWorkflowApplicationPayload) => {
      return updateWorkflowApplication(
        payload.id,
        mapUpdateWorkflowApplicationPayload(payload),
      );
    },

    onSuccess: async (): Promise<void> => {
      await queryClient.invalidateQueries({
        queryKey: workflowApplicationQueryKeys.applications(),
      });
    },
  });
}
