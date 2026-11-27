import type { FieldKind, NodeFormControl } from "../model/feed-schema.types";
import type { PublicationFieldValue } from "../model/publication-fields.types";

export interface PublicationFieldDTO {
  field_id: string;
  label: string;
  kind: FieldKind;
  required: boolean;
  min_value: number | null;
  max_value: number | null;
  min_length: number | null;
  max_length: number | null;
  min_amount: string | null;
  max_amount: string | null;
  currency: string | null;
  has_override: boolean;
  override_value: PublicationFieldValue | null;
  original_value: PublicationFieldValue | null;
  resolved_value: PublicationFieldValue | null;
  original_issues: string[];
  issues: string[];
  value_form?: NodeFormControl | null;
}
export interface PublicationFieldsDTO {
  feed_version: number;
  publication_version: number;
  readonly: boolean;
  source_available: boolean;
  fields: PublicationFieldDTO[];
}
export interface PublicationOverrideVersionsDTO {
  expected_feed_version: number;
  expected_version: number;
}
export interface SetPublicationOverrideDTO extends PublicationOverrideVersionsDTO {
  value: PublicationFieldValue;
}
export interface ChangedPublicationOverrideDTO {
  publication_version: number;
}
