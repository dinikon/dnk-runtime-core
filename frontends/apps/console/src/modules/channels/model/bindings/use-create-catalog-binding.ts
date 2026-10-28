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
  proposal: BindingProposal;
  preview: BindingPreview;
};
export function useCreateCatalogBinding(): UseMutationReturnType<
  { id: string; revision: number },
  Error,
  Input,
  ChannelScope
> {
  const cache = useQueryClient(),
    scope = useChannelScope();
  return useMutation({
    mutationFn: (v: Input) =>
      bindingApi.create(v.channelId, v.proposal, v.preview),
    retry: false,
    onMutate: () => [...scope.value] as ChannelScope,
    onSuccess: (_result, _input, previous) =>
      cache.invalidateQueries({ queryKey: channelKeys.root(previous) }),
  });
}
