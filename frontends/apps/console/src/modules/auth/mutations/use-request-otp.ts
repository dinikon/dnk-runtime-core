import { useMutation } from "@tanstack/vue-query";

import { useSessionStore } from "@/app/stores/session";

interface RequestOtpVariables {
  email: string;
}

export function useRequestOtpMutation() {
  const sessionStore = useSessionStore();

  return useMutation({
    mutationFn: ({ email }: RequestOtpVariables) =>
      sessionStore.requestEmailOtp(email),
  });
}
