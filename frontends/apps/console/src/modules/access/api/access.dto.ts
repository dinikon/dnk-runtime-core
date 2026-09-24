export interface MemberDto {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: "admin" | "member";
  status: "active" | "revoked";
  cloud_linked: boolean;
}

export interface InvitationDto {
  id: string;
  email: string;
  role: "admin" | "member";
  state: "pending" | "accepted" | "revoked" | "expired";
  expires_at: string;
}

export interface InvitationCreatedDto extends InvitationDto {
  invitation_url: string;
}
