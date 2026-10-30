import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { previewRepresentation } from "../api/representation.api";
import { useChannelScope } from "./use-channel-scope";
import { representationKeys } from "./representation.query-keys";
import type { RepresentationPreview } from "./representation.types";

export function useRepresentationPreview(
  channelId: Ref<string>,
  groupId: Ref<string>,
): UseQueryReturnType<RepresentationPreview, Error> {
  const scope = useChannelScope();
  return useQuery({
    queryKey: computed(() =>
      representationKeys.preview(scope.value, channelId.value, groupId.value),
    ),
    queryFn: ({ signal }) =>
      previewRepresentation(channelId.value, groupId.value, signal),
    enabled: computed(
      () =>
        !!scope.value[0] &&
        !!scope.value[1] &&
        !!channelId.value &&
        !!groupId.value,
    ),
    retry: false,
  });
}
