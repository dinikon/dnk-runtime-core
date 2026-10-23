import { useMutation, type UseMutationReturnType } from "@tanstack/vue-query";
import { cloudApi } from "../api/cloud.api";
import type { CloudStartInput } from "./cloud.types";

export function useStartCloudAuth(): UseMutationReturnType<
  string,
  Error,
  CloudStartInput,
  unknown
> {
  return useMutation({ mutationFn: cloudApi.start, retry: false });
}
