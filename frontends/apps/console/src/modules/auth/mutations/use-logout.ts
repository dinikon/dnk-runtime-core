import { useMutation, useQueryClient } from "@tanstack/vue-query";

import { useUserStore } from "@/app/stores/user";
import { authQueryKeys } from "@/modules/auth/model/auth.query-keys";

export function useLogoutMutation() {
  const queryClient = useQueryClient();
  const userStore = useUserStore();

  return useMutation({
    mutationFn: () => userStore.logout(),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: authQueryKeys.all });
    },
  });
}
