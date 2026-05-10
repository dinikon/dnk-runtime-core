import {httpClient} from "@/shared/api/httpClient";

export interface ResolveTenantResponse {
    exists: boolean;
    available: boolean;
    status: string;
    tenant_id: string | null;
    api_host: string | null;
}

export interface RequestEmailOtpResponse {
    token: string;
    expires_in: number;
    code?: string | null;
}

export interface ConfirmEmailOtpResponse {
    ok: boolean;
    user_id: string;
    tenant_id: string;
}

export const authApi = {
    resolveTenant: () => httpClient.get<ResolveTenantResponse>("/console/tenants/resolve"),
    requestEmailOtp: (email: string) =>
        httpClient.post<RequestEmailOtpResponse>("/console/auth/request-otp", {email}),
    confirmEmailOtp: (payload: { email: string; token: string; code: string }) =>
        httpClient.post<ConfirmEmailOtpResponse>("/console/auth/confirm-otp", payload)
};
