import { useMutation, useQueryClient } from "@tanstack/vue-query";

import { workflowAppApi } from "@/modules/workflow/api";
import type { CreateWorkflowPayload } from "@/modules/workflow/api";
import { workflowQueryKeys } from "@/modules/workflow/model/workflow.query-keys";

export function useCreateWorkflowMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateWorkflowPayload) =>
      workflowAppApi.createWorkflow(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: workflowQueryKeys.applications(),
      });
    },
  });
}
