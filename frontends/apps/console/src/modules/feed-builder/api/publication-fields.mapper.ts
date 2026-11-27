import type {
  PublicationFieldsDTO,
  PublicationOverrideVersionsDTO,
} from "./publication-fields.dto";
import type {
  PublicationFields,
  PublicationOverrideTarget,
} from "../model/publication-fields.types";

export function mapPublicationFields(
  dto: PublicationFieldsDTO,
): PublicationFields {
  return {
    feedVersion: dto.feed_version,
    publicationVersion: dto.publication_version,
    readonly: dto.readonly,
    sourceAvailable: dto.source_available,
    fields: dto.fields.map((field) => ({
      id: field.field_id,
      label: field.label,
      kind: field.kind,
      required: field.required,
      minValue: field.min_value ?? null,
      maxValue: field.max_value ?? null,
      minLength: field.min_length,
      maxLength: field.max_length,
      minAmount: field.min_amount,
      maxAmount: field.max_amount,
      currency: field.currency,
      hasOverride: field.has_override,
      overrideValue: field.override_value,
      originalValue: field.original_value,
      resolvedValue: field.resolved_value,
      originalIssues: field.original_issues,
      issues: field.issues,
      ...(field.value_form ? { valueForm: field.value_form } : {}),
    })),
  };
}

export function overrideVersions(
  target: PublicationOverrideTarget,
): PublicationOverrideVersionsDTO {
  return {
    expected_feed_version: target.feedVersion,
    expected_version: target.publicationVersion,
  };
}
