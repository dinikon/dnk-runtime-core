import type { RepresentationWriteInput } from "./representation.types";

export type ContentDeliveryStatus =
  | "queued"
  | "in_flight"
  | "succeeded"
  | "failed"
  | "unknown"
  | "blocked"
  | "cancelled";

export interface ContentDelivery {
  publicationId: string;
  externalId: string;
  role: "container" | "position";
  publicationKind: string;
  revision: number;
  requestedGeneration: number;
  sendingGeneration: number | null;
  appliedGeneration: number | null;
  status: ContentDeliveryStatus;
  confirmedFields: string[];
  errorCode: string | null;
  updatedAt: string;
  completedAt: string | null;
  contentFingerprint: string;
  recoveryRequired: boolean;
  fieldIssues: { field: string; code: string }[];
  initialErrorCode: string | null;
  lastSuccessAt: string | null;
  appliedContentFingerprint: string | null;
}

export interface RequestContentDeliveryInput extends RepresentationWriteInput {
  contentFingerprint: string;
}

export interface ReconcileContentDeliveryInput {
  channelId: string;
  groupId: string;
  publicationId: string;
  expectedRevision: number;
}

export interface ResolveContentUncertaintyInput {
  channelId: string;
  groupId: string;
  publicationId: string;
  expectedRevision: number;
  acknowledgeUnconfirmed: true;
}
