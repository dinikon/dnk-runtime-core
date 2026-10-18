import type { ChannelsFilters, PublicationsFilters } from "./channels.types";
export const channelsKeys = {
  scope: (scope: string): readonly string[] => ["channels", scope],
  platforms: (scope: string): readonly string[] => [
    "channels",
    scope,
    "platforms",
  ],
  platform: (scope: string, kind: string): readonly string[] => [
    "channels",
    scope,
    "platform",
    kind,
  ],
  references: (scope: string): readonly string[] => [
    "channels",
    scope,
    "references",
  ],
  list: (scope: string, filters: ChannelsFilters): readonly unknown[] => [
    "channels",
    scope,
    "list",
    filters,
  ],
  detail: (scope: string, id: string): readonly string[] => [
    "channels",
    scope,
    "detail",
    id,
  ],
  connection: (scope: string, id: string): readonly string[] => [
    "channels",
    scope,
    "connection",
    id,
  ],
  initialization: (scope: string, id: string): readonly string[] => [
    "channels",
    scope,
    "initialization",
    id,
  ],
  publications: (
    scope: string,
    id: string,
    filters: PublicationsFilters,
  ): readonly unknown[] => ["channels", scope, "publications", id, filters],
};
