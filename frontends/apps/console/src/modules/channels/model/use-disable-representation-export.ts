import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { disableRepresentationExport } from "../api/representation.api";
import { useChannelScope } from "./use-channel-scope";
import { representationKeys } from "./representation.query-keys";
import type { ChannelScope } from "./channel.query-keys";
import type {
  RepresentationDetails,
  RepresentationWriteInput,
} from "./representation.types";

export function useDisableRepresentationExport(): UseMutationReturnType<
  RepresentationDetails,
  Error,
  RepresentationWriteInput,
  ChannelScope
> {
  const scope = useChannelScope(),
    cache = useQueryClient();
  return useMutation({
    mutationKey: computed(() =>
      representationKeys.mutation(scope.value, "disable"),
    ),
    mutationFn: disableRepresentationExport,
    retry: false,
    onMutate: async (input) => {
      const captured = [...scope.value] as ChannelScope;
      await cache.cancelQueries({
        queryKey: representationKeys.detail(
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
      if (JSON.stringify(previous) !== JSON.stringify(scope.value)) return;
      cache.setQueryData(
        representationKeys.detail(previous, input.channelId, input.groupId),
        result,
      );
      void cache.invalidateQueries({
        queryKey: representationKeys.preview(
          previous,
          input.channelId,
          input.groupId,
        ),
        exact: true,
      });
    },
  });
}
