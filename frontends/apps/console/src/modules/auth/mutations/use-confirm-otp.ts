import { useMutation } from "@tanstack/vue-query";

import { useUserStore } from "@/app/stores/user";

interface ConfirmOtpVariables {
  code: string;
}

export function useConfirmOtpMutation() {
  const userStore = useUserStore();

  return useMutation({
    mutationFn: ({ code }: ConfirmOtpVariables) =>
      userStore.confirmEmailOtp(code),
  });
}
