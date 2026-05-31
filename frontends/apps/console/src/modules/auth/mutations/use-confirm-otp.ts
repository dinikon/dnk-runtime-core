import { useMutation } from "@tanstack/vue-query";

import { authApi } from "@/modules/auth/api/auth.api";
import type { ConfirmEmailOtpRequest } from "@/modules/auth/api/auth.contracts";

export function useConfirmOtpMutation() {
  return useMutation({
    mutationFn: (payload: ConfirmEmailOtpRequest) =>
      authApi.confirmEmailOtp(payload),
  });
}
