import type {
  ContentDelivery,
  RequestContentDeliveryInput,
  ReconcileContentDeliveryInput,
  ResolveContentUncertaintyInput,
} from "../model/content-delivery.types";
import type {
  ContentDeliveryTargetDto,
  RequestContentDeliveryDto,
  RequestContentReconciliationDto,
  ResolveContentUncertaintyDto,
} from "./content-delivery.dto";

export function contentDelivery(
  value: ContentDeliveryTargetDto,
): ContentDelivery {
  return {
    publicationId: value.publication_id,
    externalId: value.external_id,
    role: value.role,
    publicationKind: value.publication_kind,
    revision: value.revision,
    requestedGeneration: value.requested_generation,
    sendingGeneration: value.sending_generation,
    appliedGeneration: value.applied_generation,
    status: value.status,
    confirmedFields: [...value.confirmed_fields],
    errorCode: value.error_code,
    updatedAt: value.updated_at,
    completedAt: value.completed_at,
    contentFingerprint: value.content_fingerprint,
    recoveryRequired: value.recovery_required,
    fieldIssues: (value.field_issues ?? []).map((issue) => ({ ...issue })),
    initialErrorCode: value.initial_error_code ?? null,
    lastSuccessAt: value.last_success_at ?? null,
    appliedContentFingerprint: value.applied_content_fingerprint ?? null,
  };
}

export function contentDeliveryPayload(
  value: RequestContentDeliveryInput,
): RequestContentDeliveryDto {
  return {
    expected_revision: value.expectedRevision,
    expected_binding_revision: value.expectedBindingRevision,
    expected_config_revision: value.expectedConfigRevision,
    content_fingerprint: value.contentFingerprint,
  };
}

export function contentReconciliationPayload(
  value: ReconcileContentDeliveryInput,
): RequestContentReconciliationDto {
  return { expected_revision: value.expectedRevision };
}

export function contentResolutionPayload(
  value: ResolveContentUncertaintyInput,
): ResolveContentUncertaintyDto {
  return {
    expected_revision: value.expectedRevision,
    acknowledge_unconfirmed: value.acknowledgeUnconfirmed,
  };
}
