import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { publicationApi } from "../api/publication.api";
import { publicationKeys } from "./publication.query-keys";
import { useChannelScope } from "./use-channel-scope";
import type {
  PublicationFilters,
  PublicationPage,
  PublicationDetails,
  PublicationSyncRun,
} from "./publication.types";

export function usePublicationSync(
  id: Ref<string>,
): UseQueryReturnType<PublicationSyncRun | null, Error> {
  const scope = useChannelScope();
  return useQuery({
    queryKey: computed(() => publicationKeys.latest(scope.value, id.value)),
    queryFn: ({ signal }) => publicationApi.latest(id.value, signal),
    enabled: computed(() => !!id.value && !!scope.value[0] && !!scope.value[1]),
    refetchInterval: (query) =>
      query.state.data &&
      ["queued", "running"].includes(query.state.data.status) &&
      !query.state.data.recoveryRequired
        ? 2000
        : false,
  });
}
export function usePublications(
  id: Ref<string>,
  filters: Ref<PublicationFilters>,
  active: Ref<boolean>,
): UseQueryReturnType<PublicationPage, Error> {
  const scope = useChannelScope();
  return useQuery({
    queryKey: computed(() =>
      publicationKeys.list(scope.value, id.value, filters.value),
    ),
    queryFn: ({ signal }) =>
      publicationApi.list(id.value, filters.value, signal),
    enabled: computed(() => !!id.value && !!scope.value[0] && !!scope.value[1]),
    refetchInterval: computed(() => (active.value ? 2000 : false)),
  });
}
export function usePublication(
  id: Ref<string>,
  publicationId: Ref<string>,
  locale: Ref<string>,
): UseQueryReturnType<PublicationDetails, Error> {
  const scope = useChannelScope();
  return useQuery({
    queryKey: computed(() =>
      publicationKeys.detail(
        scope.value,
        id.value,
        publicationId.value,
        locale.value,
      ),
    ),
    queryFn: ({ signal }) =>
      publicationApi.get(id.value, publicationId.value, locale.value, signal),
    enabled: computed(
      () =>
        !!publicationId.value &&
        !!id.value &&
        !!scope.value[0] &&
        !!scope.value[1],
    ),
  });
}
