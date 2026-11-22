import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { publicationFieldsApi } from "../api/publication-fields.api";
import { useFeedScope } from "./use-feed-scope";
import { publicationKeys } from "./feed-publication.query-keys";
import type { PublicationFields } from "./publication-fields.types";

export function usePublicationFields(
  feedId: Ref<string>,
  publicationId: Ref<string>,
): UseQueryReturnType<PublicationFields, Error> {
  const scope = useFeedScope();
  return useQuery({
    queryKey: computed(() =>
      publicationKeys.fields(scope.value, feedId.value, publicationId.value),
    ),
    queryFn: ({ signal, queryKey }) =>
      publicationFieldsApi.get(queryKey[6], signal),
    enabled: computed(() =>
      Boolean(
        scope.value[0] && scope.value[1] && feedId.value && publicationId.value,
      ),
    ),
    retry: false,
  });
}
