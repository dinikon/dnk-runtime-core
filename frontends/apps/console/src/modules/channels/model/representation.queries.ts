import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import {
  previewRepresentation,
  getRepresentation,
} from "../api/representation.api";
import { useChannelScope } from "./use-channel-scope";
import { representationKeys } from "./representation.query-keys";
import type {
  RepresentationPreview,
  RepresentationDetails,
  RepresentationDraftInput,
} from "./representation.types";

export function useRepresentationPreview(
  channelId: Ref<string>,
  groupId: Ref<string>,
  draft?: Ref<RepresentationDraftInput | null>,
): UseQueryReturnType<RepresentationPreview, Error> {
  const scope = useChannelScope();
  return useQuery({
    queryKey: computed(() =>
      draft
        ? [
            ...representationKeys.root(
              scope.value,
              channelId.value,
              groupId.value,
            ),
            "draft",
            draft.value,
          ]
        : representationKeys.preview(
            scope.value,
            channelId.value,
            groupId.value,
          ),
    ),
    queryFn: ({ signal }) =>
      previewRepresentation(
        channelId.value,
        groupId.value,
        signal,
        draft?.value ?? undefined,
      ),
    enabled: computed(
      () =>
        !!scope.value[0] &&
        !!scope.value[1] &&
        !!channelId.value &&
        !!groupId.value &&
        (!draft || draft.value !== null),
    ),
    retry: false,
  });
}

export function useRepresentationDetails(
  channelId: Ref<string>,
  groupId: Ref<string>,
): UseQueryReturnType<RepresentationDetails, Error> {
  const scope = useChannelScope();
  return useQuery({
    queryKey: computed(() =>
      representationKeys.detail(scope.value, channelId.value, groupId.value),
    ),
    queryFn: ({ signal }) =>
      getRepresentation(channelId.value, groupId.value, signal),
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
