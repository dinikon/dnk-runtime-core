import { useMutation } from "@tanstack/vue-query";

import { useSessionStore } from "@/app/stores/session";

interface ConfirmOtpVariables {
  code: string;
}

export function useConfirmOtpMutation() {
  const sessionStore = useSessionStore();

  return useMutation({
    mutationFn: ({ code }: ConfirmOtpVariables) =>
      sessionStore.confirmEmailOtp(code),
  });
}
