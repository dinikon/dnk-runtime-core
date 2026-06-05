import { useMutation, useQueryClient } from "@tanstack/vue-query";

import { communicationApi } from "@/modules/communication/api";
import type { SendCommunicationPayload } from "@/modules/communication/api";
import { communicationQueryKeys } from "@/modules/communication/model/communication.query-keys";

export function useSendCommunicationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: SendCommunicationPayload) =>
      communicationApi.sendCommunication(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: communicationQueryKeys.outboundMessages(),
      });
    },
  });
}
