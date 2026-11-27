import type { FeedAccessToken } from "../model/feed-access.types";
import type { FeedAccessTokenDTO } from "./feed-access.dto";

export function mapFeedAccessToken(dto: FeedAccessTokenDTO): FeedAccessToken {
  return {
    id: dto.id,
    name: dto.name,
    status: dto.status,
    createdAt: dto.created_at,
    expiresAt: dto.expires_at,
    revokedAt: dto.revoked_at,
  };
}
