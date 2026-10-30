export interface ContentDeliveryTargetDto {
  publication_id: string;
  external_id: string;
  role: "container" | "position";
  publication_kind: string;
  revision: number;
  requested_generation: number;
  sending_generation: number | null;
  applied_generation: number | null;
  status:
    | "queued"
    | "in_flight"
    | "succeeded"
    | "failed"
    | "unknown"
    | "blocked"
    | "cancelled";
  confirmed_fields: string[];
  error_code: string | null;
  updated_at: string;
  completed_at: string | null;
  content_fingerprint: string;
  recovery_required: boolean;
  field_issues: { field: string; code: string }[];
  initial_error_code: string | null;
  last_success_at: string | null;
  applied_content_fingerprint: string | null;
}

export interface GetContentDeliveriesResponseDto {
  items: ContentDeliveryTargetDto[];
}
export interface RequestContentDeliveryResponseDto {
  items: ContentDeliveryTargetDto[];
}
export interface RequestContentReconciliationResponseDto {
  items: ContentDeliveryTargetDto[];
}

export interface ResolveContentUncertaintyResponseDto {
  items: ContentDeliveryTargetDto[];
}

export interface ResolveContentUncertaintyDto {
  expected_revision: number;
  acknowledge_unconfirmed: true;
}

export interface RequestContentDeliveryDto {
  expected_revision: number;
  expected_binding_revision: number;
  expected_config_revision: number;
  content_fingerprint: string;
}

export interface RequestContentReconciliationDto {
  expected_revision: number;
}
