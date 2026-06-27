import { useMutation, useQueryClient } from "@tanstack/vue-query";

import { communicationApi } from "@/modules/communication/api";
import type { UpdateProviderConnectionStatusPayload } from "@/modules/communication/api";
import { communicationQueryKeys } from "@/modules/communication/model/communication.query-keys";

export function useUpdateProviderConnectionStatusMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: UpdateProviderConnectionStatusPayload) =>
      communicationApi.updateProviderConnectionStatus(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: communicationQueryKeys.providerConnections(),
      });
    },
  });
}
