import { useMutation, useQueryClient } from "@tanstack/vue-query";

import { useSessionStore } from "@/app/stores/session";
import { authQueryKeys } from "@/modules/auth/model/auth.query-keys";

export function useLogoutMutation() {
  const queryClient = useQueryClient();
  const sessionStore = useSessionStore();

  return useMutation({
    mutationFn: () => sessionStore.logout(),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: authQueryKeys.all });
    },
  });
}
