import type {
  RuntimeFieldDescription,
  RuntimeFieldOption,
  RuntimeObjectDescription,
  RuntimeObjectFieldsResponse,
} from "@/shared/runtime-object";

export interface CompanyFieldDescriptionResponse {
  id: string;
  field_name: string;
  label: string;
  description: string;
  type: string;
  kind: string;
  is_nullable: boolean;
  default_value: string | null;
  options: RuntimeFieldOption[];
}

export interface CompanyFieldsResponse {
  object: RuntimeObjectDescription;
  fields: CompanyFieldDescriptionResponse[];
}

export type CompanyFieldDescription = RuntimeFieldDescription;
export type CompanyFieldOption = RuntimeFieldOption;
export type CompanyObjectDescription = RuntimeObjectDescription;
export type NormalizedCompanyFieldsResponse = RuntimeObjectFieldsResponse;
