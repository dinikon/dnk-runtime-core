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

export interface LogoutCurrentSessionResponse {
  ok: boolean;
}

export interface ResolveTenantResponse {
  exists: boolean;
  available: boolean;
  status: string;
  tenant_id: string | null;
  api_host: string | null;
}

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

export interface UpdateCurrentUserProfilePayload {
  last_name: string;
  first_name: string;
  middle_name: string | null;
  interface_language: string;
  interface_theme: string;
  timezone: string;
}
