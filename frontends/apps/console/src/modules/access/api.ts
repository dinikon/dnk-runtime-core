import { httpClient } from "@/app/providers/http";
import type { RequestEmailOtpResponse } from "@/modules/auth/api/auth.contracts";

export type Role = "admin" | "member";
export interface Member {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: Role;
  status: "active" | "revoked";
  cloud_linked: boolean;
}
export interface Invitation {
  id: string;
  email: string;
  role: Role;
  state: string;
  expires_at: string;
}

export const accessApi = {
  members: async () =>
    (await httpClient.get<{ users: Member[] }>("/console/users")).data.users,
  updateMember: async (
    id: string,
    payload: { role?: Role; status?: "active" | "revoked" },
  ) => (await httpClient.patch(`/console/users/${id}`, payload)).data,
  invitations: async () =>
    (
      await httpClient.get<{ invitations: Invitation[] }>(
        "/console/invitations",
      )
    ).data.invitations,
  invite: async (email: string, role: Role) =>
    (
      await httpClient.post<{ invitation_url: string }>(
        "/console/invitations",
        { email, role },
      )
    ).data,
  revokeInvitation: async (id: string) =>
    httpClient.delete(`/console/invitations/${id}`),
  requestInvitationOtp: async (invitation_token: string) =>
    (
      await httpClient.post<RequestEmailOtpResponse>(
        "/console/invitations/request-otp",
        { invitation_token },
      )
    ).data,
  acceptInvitation: async (payload: {
    invitation_token: string;
    token: string;
    code: string;
    first_name: string;
    last_name: string;
  }) => (await httpClient.post("/console/invitations/accept", payload)).data,
  cloudStatus: async () =>
    (
      await httpClient.get<{ enabled: boolean; linked: boolean }>(
        "/auth/cloud/status/",
      )
    ).data,
  cloudStart: async (purpose: "login" | "link") =>
    (
      await httpClient.post<{ authorization_url: string }>(
        "/auth/cloud/start/",
        { purpose },
      )
    ).data,
  cloudUnlink: async () => httpClient.delete("/auth/cloud/link/"),
};
