export interface RuntimeFieldOption {
  value: string;
  label: string;
}

export interface RuntimeFieldFilterCapability {
  enabled: boolean;
  operators: string[];
  input: string;
  value_type: string;
  options: RuntimeFieldOption[];
}

export interface RuntimeFieldSortCapability {
  enabled: boolean;
}

export interface RuntimeFieldDescription {
  id: string;
  field_name: string;
  label: string;
  description: string;
  type: string;
  kind: string;
  is_nullable: boolean;
  default_value: string | null;
  options: RuntimeFieldOption[];
  filter: RuntimeFieldFilterCapability;
  sort: RuntimeFieldSortCapability;
}

export interface RuntimeObjectDescription {
  id: string;
  singular_label: string;
  plural_label: string;
  description: string;
  kind: string;
}

export interface RuntimeObjectFieldsResponse {
  object: RuntimeObjectDescription;
  fields: RuntimeFieldDescription[];
}

export type RuntimeFilter =
  | RuntimeFilterCondition
  | RuntimeFilterAndGroup
  | RuntimeFilterOrGroup;

export interface RuntimeFilterCondition {
  field: string;
  op: string;
  value: unknown;
}

export interface RuntimeFilterAndGroup {
  and: RuntimeFilter[];
}

export interface RuntimeFilterOrGroup {
  or: RuntimeFilter[];
}

export interface RuntimeSort {
  field: string;
  direction: "asc" | "desc";
}

export interface RuntimePaginationRequest {
  limit: number;
  offset: number;
}

export interface RuntimeObjectSearchRequest {
  filter: RuntimeFilter | null;
  sort: RuntimeSort[];
  pagination: RuntimePaginationRequest;
}

export interface RuntimePaginationResponse {
  limit: number;
  offset: number;
  total: number;
}

export type RuntimeObjectRecord = {
  id: string;
} & Record<string, unknown>;

export interface RuntimeObjectSearchResponse<
  TRecord extends { id: string } = RuntimeObjectRecord,
> {
  data: TRecord[];
  pagination: RuntimePaginationResponse;
}

export type RuntimeObjectMutationPayload = Record<string, unknown>;

export interface RuntimeObjectResource<
  TRecord extends { id: string } = RuntimeObjectRecord,
> {
  key: string;
  describeFields: () => Promise<RuntimeObjectFieldsResponse>;
  search: (
    payload: RuntimeObjectSearchRequest,
  ) => Promise<RuntimeObjectSearchResponse<TRecord>>;
  get: (recordId: string) => Promise<TRecord>;
  create: (payload: RuntimeObjectMutationPayload) => Promise<TRecord>;
  update: (
    recordId: string,
    payload: RuntimeObjectMutationPayload,
  ) => Promise<TRecord>;
  delete: (recordId: string) => Promise<void>;
}
