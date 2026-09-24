import type { Invitation, Member } from "../model/access.types";
import type { InvitationDto, MemberDto } from "./access.dto";

function initialsFor(name: string, email: string) {
  const source = name || email.replace(/@.*/, "");
  return (
    source
      .split(/[\s._-]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("") || "U"
  );
}

export function mapMember(dto: MemberDto): Member {
  const displayName = [dto.first_name, dto.last_name]
    .map((part) => part.trim())
    .filter(Boolean)
    .join(" ");

  return {
    id: dto.id,
    email: dto.email,
    firstName: dto.first_name,
    lastName: dto.last_name,
    displayName: displayName || dto.email,
    initials: initialsFor(displayName, dto.email),
    role: dto.role,
    status: dto.status,
    cloudLinked: dto.cloud_linked,
  };
}

export function mapInvitation(dto: InvitationDto): Invitation {
  return {
    id: dto.id,
    email: dto.email,
    role: dto.role,
    state: dto.state,
    expiresAt: dto.expires_at,
  };
}
