export type FeedAccessMode = "PUBLIC" | "PRIVATE";
export type FeedAccessTokenStatus = "ACTIVE" | "EXPIRED" | "REVOKED";

export interface FeedAccessToken {
  id: string;
  name: string;
  status: FeedAccessTokenStatus;
  createdAt: string;
  expiresAt: string | null;
  revokedAt: string | null;
}

export interface IssuedFeedAccessToken {
  id: string;
  name: string;
  token: string;
}

export interface IssueFeedAccessToken {
  name: string;
  expiresAt: string | null;
}

export interface ChangedFeedAccessMode {
  accessMode: FeedAccessMode;
  feedVersion: number;
}
