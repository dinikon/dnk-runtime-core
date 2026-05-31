import { useQuery } from "@tanstack/vue-query";

import { useUserStore } from "@/app/stores/user";
import { authApi } from "@/modules/auth/api/auth.api";
import { authQueryKeys } from "@/modules/auth/model/auth.query-keys";

export function useCurrentUserQuery() {
  const userStore = useUserStore();

  return useQuery({
    queryKey: authQueryKeys.currentUser(),
    queryFn: async () => {
      const user = await authApi.getCurrentUser();
      userStore.setUser(user);
      return user;
    },
    retry: false,
  });
}
