import { useMutation, useQueryClient } from "@tanstack/vue-query";

import { communicationApi } from "@/modules/communication/api";
import type { UpdateProviderConnectorStatusPayload } from "@/modules/communication/api";
import { communicationQueryKeys } from "@/modules/communication/model/communication.query-keys";

export function useUpdateProviderConnectorStatusMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: UpdateProviderConnectorStatusPayload) =>
      communicationApi.updateProviderConnectorStatus(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: communicationQueryKeys.providerCatalog(),
      });
    },
  });
}
