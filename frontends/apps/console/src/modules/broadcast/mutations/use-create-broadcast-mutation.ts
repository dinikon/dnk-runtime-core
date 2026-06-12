import { useMutation, useQueryClient } from "@tanstack/vue-query";

import {
  broadcastApi,
  type CreateBroadcastPayload,
} from "@/modules/broadcast/api";
import { broadcastQueryKeys } from "@/modules/broadcast/model/broadcast.query-keys";

export function useCreateBroadcastMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateBroadcastPayload) =>
      broadcastApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: broadcastQueryKeys.lists(),
      });
    },
  });
}
