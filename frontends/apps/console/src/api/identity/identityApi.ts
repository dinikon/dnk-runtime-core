import {httpClient} from "@/api/http/httpClient";
import type {
    ConfirmEmailOtpRequest,
    ConfirmEmailOtpResponse,
    ConsoleUser,
    RequestEmailOtpResponse,
    ResolveTenantResponse,
    UpdateCurrentUserProfilePayload
} from "@/api/identity/types";

export const identityApi = {
    resolveTenant: async () =>
        (await httpClient.get<ResolveTenantResponse>("/console/tenants/resolve")).data,
    requestEmailOtp: async (email: string) =>
        (await httpClient.post<RequestEmailOtpResponse>("/console/auth/request-otp", {email})).data,
    confirmEmailOtp: async (payload: ConfirmEmailOtpRequest) =>
        (await httpClient.post<ConfirmEmailOtpResponse>("/console/auth/confirm-otp", payload)).data,
    getCurrentUser: async () => (await httpClient.get<ConsoleUser>("/console/auth/me")).data,
    updateCurrentUserProfile: async (payload: UpdateCurrentUserProfilePayload) =>
        (await httpClient.patch<ConsoleUser>("/console/auth/me", payload)).data
};
