export interface PublicationField {
  id: string;
  label: string;
  kind: "string" | "text" | "money";
  required: boolean;
  minLength: number | null;
  maxLength: number | null;
  minAmount: string | null;
  maxAmount: string | null;
  currency: string | null;
  hasOverride: boolean;
  overrideValue: string | null;
  originalValue: string | null;
  resolvedValue: string | null;
  originalIssues: string[];
  issues: string[];
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
  value: string;
}
export interface PublicationOverrideDraft {
  field: PublicationField;
  target: PublicationOverrideTarget;
  value: string;
}
