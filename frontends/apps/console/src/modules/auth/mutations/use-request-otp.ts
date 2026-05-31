import { useMutation } from "@tanstack/vue-query";

import { authApi } from "@/modules/auth/api/auth.api";

interface RequestOtpVariables {
  email: string;
}

export function useRequestOtpMutation() {
  return useMutation({
    mutationFn: ({ email }: RequestOtpVariables) =>
      authApi.requestEmailOtp(email),
  });
}
