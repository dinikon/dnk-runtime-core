import type { FieldKind, NodeFormControl } from "./feed-schema.types";

export type PublicationFieldValue = string | number | boolean;

export interface PublicationField {
  id: string;
  label: string;
  kind: FieldKind;
  required: boolean;
  minValue: number | null;
  maxValue: number | null;
  minLength: number | null;
  maxLength: number | null;
  minAmount: string | null;
  maxAmount: string | null;
  currency: string | null;
  hasOverride: boolean;
  overrideValue: PublicationFieldValue | null;
  originalValue: PublicationFieldValue | null;
  resolvedValue: PublicationFieldValue | null;
  originalIssues: string[];
  issues: string[];
  valueForm?: NodeFormControl;
}
export interface PublicationFields {
  feedVersion: number;
  publicationVersion: number;
  readonly: boolean;
  sourceAvailable: boolean;
  fields: PublicationField[];
}
export interface PublicationOverrideTarget {
  publicationId: string;
  fieldId: string;
  feedVersion: number;
  publicationVersion: number;
}
export interface SetPublicationOverride extends PublicationOverrideTarget {
  value: PublicationFieldValue;
}
export interface PublicationOverrideDraft {
  field: PublicationField;
  target: PublicationOverrideTarget;
  value: string;
}
