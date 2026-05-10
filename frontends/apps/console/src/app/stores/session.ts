import {defineStore} from "pinia";

import {authApi, type RequestEmailOtpResponse, type ResolveTenantResponse} from "@/shared/api/authApi";
import {HttpError, httpClient} from "@/shared/api/httpClient";

export interface ConsoleUserEmail {
    id: string;
    email: string;
    is_primary: boolean;
    is_verified: boolean;
}

export interface ConsoleUser {
    id: string;
    status: string;
    last_name: string;
    first_name: string;
    middle_name: string | null;
    avatar: string | null;
    interface_language: string;
    interface_theme: string;
    timezone: string;
    emails: ConsoleUserEmail[];
}

interface EmailChallenge {
    email: string;
    token: string;
    expiresIn: number;
    devCode: string | null;
}

interface SessionState {
    user: ConsoleUser | null;
    tenant: ResolveTenantResponse | null;
    emailChallenge: EmailChallenge | null;
    authError: string | null;
    isLoading: boolean;
    isResolvingTenant: boolean;
    isRequestingOtp: boolean;
    isConfirmingOtp: boolean;
}

export const useSessionStore = defineStore("session", {
    state: (): SessionState => ({
        user: null,
        tenant: null,
        emailChallenge: null,
        authError: null,
        isResolvingTenant: false,
        isRequestingOtp: false,
        isConfirmingOtp: false,
        isLoading: false
    }),
    getters: {
        isAuthenticated: (state) => state.user !== null,
        primaryEmail: (state) => state.user?.emails.find((email) => email.is_primary)?.email ?? null,
        isTenantAvailable: (state) => state.tenant?.exists === true && state.tenant.available === true
    },
    actions: {
        async resolveTenant() {
            this.isResolvingTenant = true;
            this.authError = null;

            try {
                this.tenant = await authApi.resolveTenant();
            } catch (error) {
                this.tenant = {
                    exists: false,
                    available: false,
                    status: error instanceof HttpError ? `http_${error.status}` : "unknown_error",
                    tenant_id: null,
                    api_host: null
                };
            } finally {
                this.isResolvingTenant = false;
            }
        },
        async requestEmailOtp(email: string): Promise<RequestEmailOtpResponse> {
            this.isRequestingOtp = true;
            this.authError = null;

            try {
                const result = await authApi.requestEmailOtp(email);
                this.emailChallenge = {
                    email,
                    token: result.token,
                    expiresIn: result.expires_in,
                    devCode: result.code ?? null
                };
                return result;
            } catch (error) {
                this.authError = authErrorMessage(error, "We could not send a verification email.");
                throw error;
            } finally {
                this.isRequestingOtp = false;
            }
        },
        async confirmEmailOtp(code: string) {
            if (!this.emailChallenge) {
                throw new Error("Email challenge is missing.");
            }

            this.isConfirmingOtp = true;
            this.authError = null;

            try {
                await authApi.confirmEmailOtp({
                    email: this.emailChallenge.email,
                    token: this.emailChallenge.token,
                    code
                });
                this.emailChallenge = null;
                await this.loadCurrentUser();
            } catch (error) {
                this.authError = authErrorMessage(error, "The verification code is invalid or expired.");
                throw error;
            } finally {
                this.isConfirmingOtp = false;
            }
        },
        async loadCurrentUser() {
            this.isLoading = true;

            try {
                this.user = await httpClient.get<ConsoleUser>("/console/auth/me");
            } catch {
                this.user = null;
            } finally {
                this.isLoading = false;
            }
        },
        clearSession() {
            this.user = null;
            this.emailChallenge = null;
            this.authError = null;
            this.isLoading = false;
        }
    }
});

function authErrorMessage(error: unknown, fallback: string): string {
    if (!(error instanceof HttpError)) {
        return fallback;
    }

    if (typeof error.detail === "string" && error.detail.trim().length > 0) {
        return error.detail;
    }

    if (
        error.detail &&
        typeof error.detail === "object" &&
        "detail" in error.detail &&
        typeof error.detail.detail === "string"
    ) {
        return error.detail.detail;
    }

    return fallback;
}
