import { httpClient } from "@/app/providers/http";
import type { RequestEmailOtpResponse } from "@/modules/auth/api/auth.contracts";
import type { InvitationInput, MemberUpdate } from "../model/access.types";
import type {
  InvitationCreatedDto,
  InvitationDto,
  MemberDto,
} from "./access.dto";
import { mapInvitation, mapMember } from "./access.mapper";

export const accessApi = {
  members: async () => {
    const response = await httpClient.get<{ users: MemberDto[] }>(
      "/console/users",
    );
    return response.data.users.map(mapMember);
  },
  updateMember: async (id: string, payload: MemberUpdate) =>
    (await httpClient.patch(`/console/users/${id}`, payload)).data,
  invitations: async () => {
    const response = await httpClient.get<{ invitations: InvitationDto[] }>(
      "/console/invitations",
    );
    return response.data.invitations.map(mapInvitation);
  },
  invite: async (input: InvitationInput) => {
    const response = await httpClient.post<InvitationCreatedDto>(
      "/console/invitations",
      input,
    );
    return {
      invitation: mapInvitation(response.data),
      invitationUrl: response.data.invitation_url,
    };
  },
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
