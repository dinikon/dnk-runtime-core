export interface ContentUpdateTextDto {
  locale: string;
  title: string | null;
  body: string | null;
}
export interface ContentUpdateItemDto {
  publication_id: string;
  catalog_item_id: string;
  external_id: string;
  desired: ContentUpdateTextDto[];
  observed: ContentUpdateTextDto[];
  status: string;
  issues: string[];
  attempts: number;
}
export interface GetContentUpdateResponseDto {
  id: string;
  channel_id: string;
  status: string;
  revision: number;
  sequence: number;
  preview_hash: string | null;
  created_at: string;
  expires_at: string;
  confirmed_at: string | null;
  outbound_enabled: boolean;
  interrupted: boolean;
  items: ContentUpdateItemDto[];
}
export interface StartContentUpdateRequestDto {
  run_id: string;
  publication_ids: string[];
}
export interface StartContentUpdateResponseDto {
  run_id: string;
}
export interface ConfirmContentUpdateRequestDto {
  expected_revision: number;
  preview_hash: string;
}
export interface ConfirmContentUpdateResponseDto {
  run_id: string;
}
export interface RetryContentUpdateRequestDto {
  expected_revision: number;
}
export interface RetryContentUpdateResponseDto {
  run_id: string;
}
export interface ListContentUpdatesResponseDto {
  items: { id: string; status: string; created_at: string; total: number }[];
}
export interface SetOutboundRequestDto {
  revision: number;
  is_enabled: boolean;
}
export interface SetOutboundResponseDto {
  channel_id: string;
  revision: number;
}
