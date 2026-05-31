import { useMutation } from "@tanstack/vue-query";

import { useUserStore } from "@/app/stores/user";

interface RequestOtpVariables {
  email: string;
}

export function useRequestOtpMutation() {
  const userStore = useUserStore();

  return useMutation({
    mutationFn: ({ email }: RequestOtpVariables) =>
      userStore.requestEmailOtp(email),
  });
}
