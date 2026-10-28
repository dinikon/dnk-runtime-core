import { channelKeys, type ChannelScope } from "./channel.query-keys";
import type { PublicationFilters } from "./publication.types";
export const publicationKeys = {
  root: (scope: ChannelScope, id: string) =>
    [...channelKeys.root(scope), "publications", id] as const,
  list: (scope: ChannelScope, id: string, filters: PublicationFilters) =>
    [...publicationKeys.root(scope, id), "list", filters] as const,
  detail: (
    scope: ChannelScope,
    id: string,
    publicationId: string,
    locale: string,
  ) =>
    [
      ...publicationKeys.root(scope, id),
      "detail",
      publicationId,
      locale,
    ] as const,
  latest: (scope: ChannelScope, id: string) =>
    [...channelKeys.root(scope), "sync-run", id] as const,
};
