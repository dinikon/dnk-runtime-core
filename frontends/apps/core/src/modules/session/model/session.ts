import { useState } from "#imports";
import { ApiError, apiRequest, setCsrfToken } from "../../../shared/api";

export interface CoreUser {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  middle_name: string;
  display_name: string;
  initials: string;
}

interface SessionState {
  authenticated: boolean | null;
  showAdminLink: boolean;
  user: CoreUser | null;
  loading: boolean;
  error: boolean;
}
let pending: Promise<void> | null = null;

export function useCoreSession() {
  const session = useState<SessionState>("core-session", () => ({
    authenticated: null,
    showAdminLink: false,
    user: null,
    loading: false,
    error: false,
  }));

  function refreshSession(): Promise<void> {
    // Keep identity out of SSR output and isolate state per Nuxt request.
    if (import.meta.server) return Promise.resolve();
    if (pending) return pending;
    const state = session.value;
    state.loading = true;
    state.error = false;
    pending = (async () => {
      try {
        const result = await apiRequest<{ authenticated: boolean; csrfToken: string; showAdminLink?: boolean }>("/api/session/");
        setCsrfToken(result.csrfToken);
        state.authenticated = result.authenticated;
        state.showAdminLink = result.authenticated && result.showAdminLink === true;
        if (result.authenticated) {
          state.user = await apiRequest<CoreUser>("/api/me/");
        } else {
          state.user = null;
        }
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          state.authenticated = false;
          state.showAdminLink = false;
          state.user = null;
        } else {
          // A failed connection does not prove that the session has expired.
          state.error = true;
        }
      } finally {
        state.loading = false;
        pending = null;
      }
    })();
    return pending;
  }
  return { session, refreshSession };
}

export function loginUrl(next = "/app/"): string {
  const isLocal = next.startsWith("/") && !next.startsWith("//") && !next.includes("\\");
  return `/accounts/login/?next=${encodeURIComponent(isLocal ? next : "/app/")}`;
}
