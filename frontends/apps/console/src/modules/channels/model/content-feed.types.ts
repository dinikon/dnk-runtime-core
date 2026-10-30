export interface ContentFeed {
  id: string;
  revision: number;
  enabled: boolean;
  scopeKey: string;
  publicUrl: string | null;
  updatedAt: string;
}
export interface FeedPreview {
  ready: boolean;
  statistics: {
    offers: number;
    changedOffers: number;
    categories: number;
  } | null;
  issues: {
    code: string;
    publicationId: string | null;
    field: string | null;
  }[];
}
export type FeedPhase =
  | "idle"
  | "queued"
  | "submitting"
  | "processing"
  | "verifying"
  | "completed"
  | "failed"
  | "unknown"
  | "needs_attention"
  | "resolved";
export interface FeedImport {
  revision: number;
  phase: FeedPhase;
  operationId: string | null;
  externalId: string | null;
  submission:
    "not_sent" | "queued" | "submitting" | "accepted" | "rejected" | "unknown";
  forceUpdate: boolean;
  requestedAt: string | null;
  checkedAt: string | null;
  finishedAt: string | null;
  errorCode: string | null;
  manualResolution: string | null;
  report: {
    status: "SUCCESS" | "PARTIAL" | "FATAL";
    total: number | null;
    updated: number | null;
    created: number | null;
    imported: number | null;
    notChanged: number | null;
    notInFile: number | null;
    withErrors: number | null;
    issues: { code: string; stage: string }[];
  } | null;
  verification: {
    publicationId: string;
    externalId: string;
    importKey: string;
    fields: {
      field: "title" | "body" | "gallery";
      locale: string | null;
      status: "confirmed" | "mismatch" | "unconfirmed" | "obsolete";
    }[];
    observedGallery: string[];
  }[];
  recoveryRequired: boolean;
  canStart: boolean;
  canResume: boolean;
  canAttach: boolean;
  canResolve: boolean;
}
export interface FeedLocation {
  channelId: string;
  feedId: string;
}
export interface CreateFeedInput {
  channelId: string;
  sourceUrl: string;
}
export interface SaveFeedInput extends FeedLocation {
  sourceUrl: string;
  expectedRevision: number;
}
export interface FeedRevisionInput extends FeedLocation {
  expectedRevision: number;
}
export interface FeedImportRevisionInput extends FeedRevisionInput {
  expectedDeliveryRevision: number;
}
export interface RequestFeedImportInput extends FeedImportRevisionInput {
  requestId: string;
  forceUpdate: boolean;
}
export interface AttachFeedImportInput extends FeedImportRevisionInput {
  externalId: string;
}
export interface ResolveFeedImportInput extends FeedImportRevisionInput {
  confirmNotSubmitted: true;
}
