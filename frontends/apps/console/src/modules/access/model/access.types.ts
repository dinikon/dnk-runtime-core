export type Role = "admin" | "member";
export type MemberStatus = "active" | "revoked";
export type InvitationState = "pending" | "accepted" | "revoked" | "expired";
export type UsersTab = "members" | "invitations";

export interface Member {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  displayName: string;
  initials: string;
  role: Role;
  status: MemberStatus;
  cloudLinked: boolean;
}

export interface Invitation {
  id: string;
  email: string;
  role: Role;
  state: InvitationState;
  expiresAt: string;
}

export interface InvitationInput {
  email: string;
  role: Role;
}

export interface MemberUpdate {
  role?: Role;
  status?: MemberStatus;
}

export interface InvitationResult {
  email: string;
  role: Role;
  ok: boolean;
  invitationUrl?: string;
  message?: string;
}
