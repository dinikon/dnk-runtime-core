import { useMutation, useQueryClient } from "@tanstack/vue-query";

import { useUserStore } from "@/app/stores/user";
import { authApi } from "@/modules/auth/api/auth.api";
import { authQueryKeys } from "@/modules/auth/model/auth.query-keys";

export function useLogoutMutation() {
  const queryClient = useQueryClient();
  const userStore = useUserStore();

  return useMutation({
    mutationFn: async () => {
      try {
        return await authApi.logoutCurrentSession();
      } catch {
        // Logout is treated as local cleanup even if the server session is already invalid.
        return { ok: true };
      } finally {
        userStore.clearUser();
      }
    },
    onSettled: () => {
      queryClient.removeQueries({ queryKey: authQueryKeys.all });
    },
  });
}
