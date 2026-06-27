import { useMutation, useQueryClient } from "@tanstack/vue-query";

import { communicationApi } from "@/modules/communication/api";
import { communicationQueryKeys } from "@/modules/communication/model/communication.query-keys";

export function useDeleteProviderConnectionMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: communicationApi.deleteProviderConnection,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: communicationQueryKeys.providerConnections(),
      });
    },
  });
}
