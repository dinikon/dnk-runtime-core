import { useMutation, useQueryClient } from "@tanstack/vue-query";

import { communicationApi } from "@/modules/communication/api";
import type { CreateProviderConnectionPayload } from "@/modules/communication/api";
import { communicationQueryKeys } from "@/modules/communication/model/communication.query-keys";

export function useCreateProviderConnectionMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateProviderConnectionPayload) =>
      communicationApi.createProviderConnection(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: communicationQueryKeys.providerConnections(),
      });
    },
  });
}
