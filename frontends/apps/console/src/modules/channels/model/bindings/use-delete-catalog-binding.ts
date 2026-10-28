import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { useChannelScope } from "../use-channel-scope";
import { bindingApi } from "../../api/binding.api";
import { channelKeys, type ChannelScope } from "../channel.query-keys";

type Input = { channelId: string; id: string; revision: number };
export function useDeleteCatalogBinding(): UseMutationReturnType<
  void,
  Error,
  Input,
  ChannelScope
> {
  const cache = useQueryClient(),
    scope = useChannelScope();
  return useMutation({
    mutationFn: (v: Input) => bindingApi.remove(v.channelId, v.id, v.revision),
    retry: false,
    onMutate: () => [...scope.value] as ChannelScope,
    onSuccess: (_result, _input, previous) =>
      cache.invalidateQueries({ queryKey: channelKeys.root(previous) }),
  });
}
