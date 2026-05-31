import {defineStore} from "pinia";

import {getApiErrorMessage, getApiErrorStatus} from "@/app/providers/http";
import {
    authApi,
    type ConsoleUser,
    type RequestEmailOtpResponse,
    type ResolveTenantResponse,
    type UpdateCurrentUserProfilePayload
} from "@/modules/auth/api";

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
    isUpdatingProfile: boolean;
    isLoggingOut: boolean;
}

interface UpdateProfileNameInput {
    first_name: string;
    last_name: string;
    middle_name: string | null;
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
        isUpdatingProfile: false,
        isLoggingOut: false,
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
                const status = getApiErrorStatus(error);
                this.tenant = {
                    exists: false,
                    available: false,
                    status: status ? `http_${status}` : "unknown_error",
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
                this.authError = getApiErrorMessage(error, "We could not send a verification email.");
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
                this.authError = getApiErrorMessage(error, "The verification code is invalid or expired.");
                throw error;
            } finally {
                this.isConfirmingOtp = false;
            }
        },
        async loadCurrentUser() {
            this.isLoading = true;

            try {
                this.user = await authApi.getCurrentUser();
            } catch {
                this.user = null;
            } finally {
                this.isLoading = false;
            }
        },
        async logout() {
            this.isLoggingOut = true;
            this.authError = null;

            try {
                await authApi.logoutCurrentSession();
            } catch {
                // Logout is treated as local cleanup even if the server no longer has a valid session.
            } finally {
                this.clearSession();
                this.isLoggingOut = false;
            }
        },
        async updateProfileName(input: UpdateProfileNameInput) {
            if (!this.user) {
                throw new Error("Current user is not loaded.");
            }

            this.isUpdatingProfile = true;

            try {
                const payload: UpdateCurrentUserProfilePayload = {
                    first_name: input.first_name,
                    last_name: input.last_name,
                    middle_name: input.middle_name,
                    interface_language: this.user.interface_language,
                    interface_theme: this.user.interface_theme,
                    timezone: this.user.timezone
                };
                this.user = await authApi.updateCurrentUserProfile(payload);
                return this.user;
            } finally {
                this.isUpdatingProfile = false;
            }
        },
        clearSession() {
            this.user = null;
            this.emailChallenge = null;
            this.authError = null;
            this.isLoading = false;
            this.isConfirmingOtp = false;
            this.isRequestingOtp = false;
            this.isLoggingOut = false;
            this.isUpdatingProfile = false;
        }
    }
});
