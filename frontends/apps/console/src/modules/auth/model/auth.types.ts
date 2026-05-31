import type {
  ConsoleUser,
  ResolveTenantResponse,
} from "@/modules/auth/api/auth.contracts";

export type AuthLoginStep =
  | "checking"
  | "workspace-not-found"
  | "request-otp"
  | "confirm-otp";

export interface EmailChallenge {
  email: string;
  token: string;
  expiresIn: number;
  devCode: string | null;
}

export interface AuthTenantState {
  tenant: ResolveTenantResponse | null;
  isResolvingTenant: boolean;
}

export interface AuthUserState {
  user: ConsoleUser | null;
  emailChallenge: EmailChallenge | null;
  authError: string | null;
  isLoading: boolean;
  isRequestingOtp: boolean;
  isConfirmingOtp: boolean;
  isUpdatingProfile: boolean;
  isLoggingOut: boolean;
}

export interface UpdateProfileNameInput {
  first_name: string;
  last_name: string;
  middle_name: string | null;
}
