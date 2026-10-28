import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { useChannelScope } from "../use-channel-scope";
import { bindingKeys } from "./binding.query-keys";
import { bindingApi } from "../../api/binding.api";
import type {
  BindingFilters,
  BindingPage,
  BindingCandidateFilters,
  BindingCandidates,
  BindingProposal,
  BindingPreview,
  CatalogBinding,
} from "./binding.types";
export function useCatalogBindings(
  filters: Ref<BindingFilters>,
): UseQueryReturnType<BindingPage, Error> {
  const scope = useChannelScope();
  return useQuery({
    queryKey: computed(() => bindingKeys.list(scope.value, filters.value)),
    queryFn: ({ signal }) => bindingApi.list(filters.value, signal),
    enabled: computed(
      () =>
        !!scope.value[0] &&
        !!scope.value[1] &&
        !!(filters.value.catalogRootId || filters.value.channelId),
    ),
    retry: false,
  });
}
export function useBindingCandidates(
  kind: "catalog" | "publication",
  filters: Ref<BindingCandidateFilters>,
  enabled: Ref<boolean>,
): UseQueryReturnType<BindingCandidates, Error> {
  const scope = useChannelScope();
  return useQuery({
    queryKey: computed(() =>
      bindingKeys.candidates(scope.value, kind, filters.value),
    ),
    queryFn: ({ signal }) => bindingApi.candidates(kind, filters.value, signal),
    enabled: computed(
      () => enabled.value && !!scope.value[0] && !!filters.value.channelId,
    ),
    retry: false,
  });
}

export function useBindingPreview(
  channel: Ref<string>,
  proposal: Ref<BindingProposal>,
  enabled: Ref<boolean>,
): UseQueryReturnType<BindingPreview, Error> {
  const scope = useChannelScope();
  return useQuery({
    queryKey: computed(() => [
      ...bindingKeys.root(scope.value),
      "preview",
      channel.value,
      proposal.value,
    ]),
    queryFn: ({ signal }) =>
      bindingApi.preview(channel.value, proposal.value, signal),
    enabled: computed(
      () =>
        enabled.value &&
        !!scope.value[0] &&
        !!proposal.value.catalogRootId &&
        !!channel.value,
    ),
    retry: false,
  });
}
export function useCatalogBinding(
  channel: Ref<string>,
  id: Ref<string>,
  locale: Ref<string>,
): UseQueryReturnType<CatalogBinding, Error> {
  const scope = useChannelScope();
  return useQuery({
    queryKey: computed(() =>
      bindingKeys.detail(scope.value, channel.value, id.value, locale.value),
    ),
    queryFn: ({ signal }) =>
      bindingApi.get(channel.value, id.value, locale.value, signal),
    enabled: computed(
      () =>
        !!scope.value[0] && !!channel.value && !!id.value && id.value !== "new",
    ),
    retry: false,
  });
}
