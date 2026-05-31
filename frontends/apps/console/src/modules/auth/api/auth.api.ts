import { httpClient } from "@/app/providers/http";
import type {
  ConfirmEmailOtpRequest,
  ConfirmEmailOtpResponse,
  ConsoleUser,
  LogoutCurrentSessionResponse,
  RequestEmailOtpResponse,
  ResolveTenantResponse,
  UpdateCurrentUserProfilePayload,
} from "@/modules/auth/api/types";

export const authApi = {
  resolveTenant: async () =>
    (await httpClient.get<ResolveTenantResponse>("/console/tenants/resolve"))
      .data,
  requestEmailOtp: async (email: string) =>
    (
      await httpClient.post<RequestEmailOtpResponse>(
        "/console/auth/request-otp",
        { email },
      )
    ).data,
  confirmEmailOtp: async (payload: ConfirmEmailOtpRequest) =>
    (
      await httpClient.post<ConfirmEmailOtpResponse>(
        "/console/auth/confirm-otp",
        payload,
      )
    ).data,
  getCurrentUser: async () =>
    (await httpClient.get<ConsoleUser>("/console/auth/me")).data,
  updateCurrentUserProfile: async (payload: UpdateCurrentUserProfilePayload) =>
    (await httpClient.patch<ConsoleUser>("/console/auth/me", payload)).data,
  logoutCurrentSession: async () =>
    (
      await httpClient.post<LogoutCurrentSessionResponse>(
        "/console/auth/logout",
      )
    ).data,
};
