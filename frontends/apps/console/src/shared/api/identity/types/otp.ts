export interface RequestEmailOtpResponse {
    token: string;
    expires_in: number;
    code?: string | null;
}

export interface ConfirmEmailOtpRequest {
    email: string;
    token: string;
    code: string;
}

export interface ConfirmEmailOtpResponse {
    ok: boolean;
    user_id: string;
    tenant_id: string;
}
