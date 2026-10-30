import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { requestContentReconciliation } from "../api/content-delivery.api";
import { useChannelScope } from "./use-channel-scope";
import { contentDeliveryKeys } from "./content-delivery.query-keys";
import type { ChannelScope } from "./channel.query-keys";
import type {
  ContentDelivery,
  ReconcileContentDeliveryInput,
} from "./content-delivery.types";

export function useReconcileContentDelivery(): UseMutationReturnType<
  ContentDelivery[],
  Error,
  ReconcileContentDeliveryInput,
  ChannelScope
> {
  const scope = useChannelScope(),
    cache = useQueryClient();
  return useMutation({
    mutationKey: computed(() =>
      contentDeliveryKeys.mutation(scope.value, "reconcile"),
    ),
    mutationFn: requestContentReconciliation,
    retry: false,
    onMutate: async (input) => {
      const captured = [...scope.value] as ChannelScope;
      await cache.cancelQueries({
        queryKey: contentDeliveryKeys.detail(
          captured,
          input.channelId,
          input.groupId,
        ),
        exact: true,
      });
      if (JSON.stringify(captured) !== JSON.stringify(scope.value))
        throw new Error("Рабочее пространство изменилось. Обновите страницу.");
      return captured;
    },
    onSuccess: (result, input, previous) => {
      if (!previous || JSON.stringify(previous) !== JSON.stringify(scope.value))
        return;
      cache.setQueryData(
        contentDeliveryKeys.detail(previous, input.channelId, input.groupId),
        result,
      );
      void cache.invalidateQueries({
        queryKey: contentDeliveryKeys.detail(
          previous,
          input.channelId,
          input.groupId,
        ),
        exact: true,
      });
    },
  });
}
