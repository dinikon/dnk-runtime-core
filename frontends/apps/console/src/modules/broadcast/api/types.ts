import type {
  RuntimeObjectFieldsResponse,
  RuntimeObjectRecord,
  RuntimeObjectSearchRequest,
  RuntimeObjectSearchResponse,
} from "@/shared/runtime-object";

export type BroadcastStatus = string;

export interface BroadcastListItem extends RuntimeObjectRecord {
  id: string;
  created_at: string;
  updated_at: string;
  title: string;
  description: string | null;
  status: BroadcastStatus;
}

export type BroadcastFieldsResponse = RuntimeObjectFieldsResponse;

export type ListBroadcastsPayload = RuntimeObjectSearchRequest;

export type ListBroadcastsResponse =
  RuntimeObjectSearchResponse<BroadcastListItem>;

export interface CreateBroadcastPayload {
  title: string;
  description: string | null;
}

export type BroadcastResponse = BroadcastListItem;
