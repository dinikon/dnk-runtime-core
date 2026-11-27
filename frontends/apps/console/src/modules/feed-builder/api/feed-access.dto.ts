import type { FeedAccessMode, FeedAccessTokenStatus } from "../model/feed-access.types";

export interface FeedAccessTokenDTO {
  id: string;
  name: string;
  status: FeedAccessTokenStatus;
  created_at: string;
  expires_at: string | null;
  revoked_at: string | null;
}

export interface ListFeedAccessTokensDTO {
  items: FeedAccessTokenDTO[];
}

export interface IssuedFeedAccessTokenDTO {
  id: string;
  name: string;
  token: string;
  created_at: string;
  expires_at: string | null;
}

export interface ChangedFeedAccessModeDTO {
  access_mode: FeedAccessMode;
  feed_version: number;
}
