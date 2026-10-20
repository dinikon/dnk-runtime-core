export interface ContentText {
  locale: string;
  title: string | null;
  body: string | null;
}
export interface ContentUpdateItem {
  publicationId: string;
  catalogItemId: string;
  externalId: string;
  desired: ContentText[];
  observed: ContentText[];
  status: string;
  issues: string[];
  attempts: number;
}
export interface ContentUpdate {
  id: string;
  channelId: string;
  status: string;
  revision: number;
  sequence: number;
  previewHash: string | null;
  createdAt: string;
  expiresAt: string;
  confirmedAt: string | null;
  outboundEnabled: boolean;
  interrupted: boolean;
  items: ContentUpdateItem[];
}
export interface ContentUpdateSummary {
  id: string;
  status: string;
  createdAt: string;
  total: number;
}
export interface StartContentUpdateInput {
  runId: string;
  channelId: string;
  publicationIds: string[];
}
export interface ConfirmContentUpdateInput {
  runId: string;
  revision: number;
  previewHash: string;
}
export interface RetryContentUpdateInput {
  runId: string;
  revision: number;
}
export interface SetOutboundInput {
  channelId: string;
  revision: number;
  enabled: boolean;
}
