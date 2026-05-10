import {httpClient} from "@/shared/api/http/httpClient";
import type {
    ConfirmEmailOtpRequest,
    ConfirmEmailOtpResponse,
    ConsoleUser,
    RequestEmailOtpResponse,
    ResolveTenantResponse
} from "@/shared/api/identity/types";

export const identityApi = {
    resolveTenant: async () =>
        (await httpClient.get<ResolveTenantResponse>("/console/tenants/resolve")).data,
    requestEmailOtp: async (email: string) =>
        (await httpClient.post<RequestEmailOtpResponse>("/console/auth/request-otp", {email})).data,
    confirmEmailOtp: async (payload: ConfirmEmailOtpRequest) =>
        (await httpClient.post<ConfirmEmailOtpResponse>("/console/auth/confirm-otp", payload)).data,
    getCurrentUser: async () => (await httpClient.get<ConsoleUser>("/console/auth/me")).data
};
