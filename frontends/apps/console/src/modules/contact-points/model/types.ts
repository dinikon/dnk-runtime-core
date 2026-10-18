import type { CountryCode } from "libphonenumber-js";

export type ContactPointKind = "phone" | "email";
export interface ContactPointDraft {
  clientKey: string;
  bindingId?: string;
  contactPointId?: string;
  value: string;
  labelId: string | null;
  countryCode?: CountryCode;
}
export interface ContactPointLabel {
  id: string;
  type: ContactPointKind;
  name: string;
  isActive: boolean;
}
export interface ContactPointDto {
  binding_id: string;
  contact_point_id: string;
  value: string;
  label_id: string | null;
  country_code: CountryCode | null;
}
export interface ContactPointArrays {
  phones: ContactPointDraft[];
  emails: ContactPointDraft[];
}
export type ContactPointErrors = Record<
  string,
  Partial<Record<"value" | "labelId" | "countryCode" | "bindingId", string>>
>;
export interface ContactPointsFieldProps {
  modelValue: ContactPointDraft[];
  labels: ContactPointLabel[];
  disabled?: boolean;
  pending?: boolean;
  attempted?: boolean;
  errors?: ContactPointErrors;
  labelsLoading?: boolean;
  labelsError?: boolean;
}
