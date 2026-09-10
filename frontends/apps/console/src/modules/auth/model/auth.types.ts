import type { ResolveTenantResponse } from "@/modules/auth/api/auth.contracts";

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
