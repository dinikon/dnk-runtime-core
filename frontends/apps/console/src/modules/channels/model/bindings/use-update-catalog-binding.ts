import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { useChannelScope } from "../use-channel-scope";
import { bindingApi } from "../../api/binding.api";
import { channelKeys, type ChannelScope } from "../channel.query-keys";
import type { BindingProposal, BindingPreview } from "./binding.types";
type Input = {
  channelId: string;
  id: string;
  revision: number;
  proposal: BindingProposal;
  preview: BindingPreview;
};
export function useUpdateCatalogBinding(): UseMutationReturnType<
  { id: string; revision: number },
  Error,
  Input,
  ChannelScope
> {
  const cache = useQueryClient(),
    scope = useChannelScope();
  return useMutation({
    mutationFn: (v: Input) =>
      bindingApi.update(v.channelId, v.id, v.revision, v.proposal, v.preview),
    retry: false,
    onMutate: () => [...scope.value] as ChannelScope,
    onSuccess: (_result, _input, previous) =>
      cache.invalidateQueries({ queryKey: channelKeys.root(previous) }),
  });
}
