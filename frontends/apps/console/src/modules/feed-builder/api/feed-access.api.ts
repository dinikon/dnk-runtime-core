import { httpClient } from "@/app/providers/http";
import { feedRequest } from "./feed-request";
import { mapFeedAccessToken } from "./feed-access.mapper";
import type {
  ChangedFeedAccessModeDTO, IssuedFeedAccessTokenDTO, ListFeedAccessTokensDTO,
} from "./feed-access.dto";
import type {
  ChangedFeedAccessMode, FeedAccessMode, FeedAccessToken,
  IssuedFeedAccessToken, IssueFeedAccessToken,
} from "../model/feed-access.types";

function root(feedId: string): string {
  return `/console/feed-builder/feeds/${encodeURIComponent(feedId)}`;
}

export const feedAccessApi = {
  list(feedId: string, signal: AbortSignal): Promise<FeedAccessToken[]> {
    return feedRequest(async () => {
      const { data } = await httpClient.get<ListFeedAccessTokensDTO>(
        `${root(feedId)}/access-tokens`, { signal },
      );
      return data.items.map(mapFeedAccessToken);
    });
  },
  change(feedId: string, version: number, mode: FeedAccessMode, signal: AbortSignal): Promise<ChangedFeedAccessMode> {
    return feedRequest(async () => {
      const { data } = await httpClient.patch<ChangedFeedAccessModeDTO>(
        `${root(feedId)}/access`, { expected_version: version, access_mode: mode }, { signal },
      );
      return { accessMode: data.access_mode, feedVersion: data.feed_version };
    });
  },
  issue(feedId: string, input: IssueFeedAccessToken, signal: AbortSignal): Promise<IssuedFeedAccessToken> {
    return feedRequest(async () => {
      const { data } = await httpClient.post<IssuedFeedAccessTokenDTO>(
        `${root(feedId)}/access-tokens`, { name: input.name, expires_at: input.expiresAt }, { signal },
      );
      return { id: data.id, name: data.name, token: data.token };
    });
  },
  revoke(feedId: string, tokenId: string, signal: AbortSignal): Promise<void> {
    return feedRequest(async () => {
      await httpClient.delete(`${root(feedId)}/access-tokens/${encodeURIComponent(tokenId)}`, { signal });
    });
  },
};
