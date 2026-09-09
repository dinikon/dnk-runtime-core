import { useState } from "#imports";
import { apiRequest } from "../../../shared/api";

export interface CoreCapabilities {
  registrationEnabled: boolean;
  passwordLoginEnabled: boolean;
  emailCodeLoginEnabled: boolean;
  phoneCodeLoginEnabled: boolean;
  phoneLoginMode: "any_verified" | "primary_only";
  passkeyLoginEnabled: boolean;
  passkeySignupEnabled: boolean;
  providers: Array<"google" | "github" | "telegram">;
}

interface CapabilitiesState {
  data: CoreCapabilities | null;
  loading: boolean;
  error: boolean;
}

let pending: Promise<void> | null = null;

export function useCoreCapabilities() {
  const capabilities = useState<CapabilitiesState>("core-capabilities", () => ({
    data: null,
    loading: false,
    error: false,
  }));

  function refreshCapabilities(): Promise<void> {
    // The public Hero remains server-rendered while its actions follow server policy.
    if (import.meta.server) return Promise.resolve();
    if (pending) return pending;
    const state = capabilities.value;
    state.loading = true;
    state.error = false;
    pending = (async () => {
      try {
        state.data = await apiRequest<CoreCapabilities>("/api/capabilities/");
      } catch {
        // A configuration lookup must never change the user's session state.
        state.error = true;
      } finally {
        state.loading = false;
        pending = null;
      }
    })();
    return pending;
  }

  return { capabilities, refreshCapabilities };
}
