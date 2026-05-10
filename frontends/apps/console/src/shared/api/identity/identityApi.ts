import {httpClient} from "@/shared/api/http/httpClient";
import type {
    ConfirmEmailOtpRequest,
    ConfirmEmailOtpResponse,
    ConsoleUser,
    RequestEmailOtpResponse,
    ResolveTenantResponse
} from "@/shared/api/identity/types";

export const identityApi = {
    resolveTenant: () => httpClient.get<ResolveTenantResponse>("/console/tenants/resolve"),
    requestEmailOtp: (email: string) =>
        httpClient.post<RequestEmailOtpResponse>("/console/auth/request-otp", {email}),
    confirmEmailOtp: (payload: ConfirmEmailOtpRequest) =>
        httpClient.post<ConfirmEmailOtpResponse>("/console/auth/confirm-otp", payload),
    getCurrentUser: () => httpClient.get<ConsoleUser>("/console/auth/me")
};
