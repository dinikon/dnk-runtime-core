import type { ChannelsFilters, PublicationsFilters } from "./channels.types";
import type {
  CatalogCandidatesInput,
  DraftPreviewInput,
} from "./catalog-links.types";
export const channelsKeys = {
  batchOverview: (scope: string, id: string): readonly string[] => [
    "channels",
    scope,
    "batch-overview",
    id,
  ],
  batchDetail: (
    scope: string,
    input: { runId: string; offset: number; limit: number },
  ): readonly unknown[] => ["channels", scope, "batch-detail", input],
  contentUpdate: (scope: string, id: string): readonly string[] => [
    "channels",
    scope,
    "content-update",
    id,
  ],
  contentUpdates: (scope: string, id: string): readonly string[] => [
    "channels",
    scope,
    "content-updates",
    id,
  ],
  publicationImport: (scope: string, id: string): readonly string[] => [
    "channels",
    scope,
    "publication-import",
    id,
  ],
  candidates: (
    scope: string,
    input: CatalogCandidatesInput,
  ): readonly unknown[] => ["channels", scope, "catalog-candidates", input],
  draftPreview: (
    scope: string,
    input: DraftPreviewInput,
  ): readonly unknown[] => ["channels", scope, "draft-preview", input],
  publicationSnapshot: (scope: string, id: string): readonly string[] => [
    "channels",
    scope,
    "publication-snapshot",
    id,
  ],
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
