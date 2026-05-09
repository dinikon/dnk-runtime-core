import {defineStore} from "pinia";

import {httpClient} from "@/shared/api/httpClient";

export interface ConsoleUser {
    id: string;
    email: string;
    name?: string | null;
    interfaceTheme?: string;
}

interface SessionState {
    user: ConsoleUser | null;
    isLoading: boolean;
}

export const useSessionStore = defineStore("session", {
    state: (): SessionState => ({
        user: null,
        isLoading: false
    }),
    getters: {
        isAuthenticated: (state) => state.user !== null
    },
    actions: {
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
            this.isLoading = false;
        }
    }
});
