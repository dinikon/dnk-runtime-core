import { httpClient } from "@/app/providers/http";
import type {
  Company,
  CompanyFieldsResponse,
  CreateCompanyPayload,
  ListCompaniesResponse,
  NormalizedCompanyFieldsResponse,
  UpdateCompanyPayload,
} from "@/modules/console/crm/api/types";
import type {
  RuntimeFieldDescription,
  RuntimeObjectMutationPayload,
  RuntimeObjectSearchRequest,
  RuntimeObjectSearchResponse,
} from "@/shared/runtime-object";

export const crmCompaniesApi = {
  describeFields: async () =>
    normalizeCompanyFieldsResponse(
      (
        await httpClient.post<CompanyFieldsResponse>(
          "/console/crm/companies/fields",
        )
      ).data,
    ),
  search: async (payload: RuntimeObjectSearchRequest) => {
    const response = (
      await httpClient.get<ListCompaniesResponse>("/console/crm/companies", {
        params: payload.pagination,
      })
    ).data;

    return {
      data: response.items,
      pagination: {
        limit: response.limit,
        offset: response.offset,
        total: response.offset + response.count,
      },
    } satisfies RuntimeObjectSearchResponse<Company>;
  },
  list: async (params: { limit?: number; offset?: number } = {}) =>
    (
      await httpClient.get<ListCompaniesResponse>("/console/crm/companies", {
        params,
      })
    ).data,
  get: async (companyId: string) =>
    (await httpClient.get<Company>(`/console/crm/companies/${companyId}`)).data,
  create: async (
    payload: CreateCompanyPayload | RuntimeObjectMutationPayload,
  ) => (await httpClient.post<Company>("/console/crm/companies", payload)).data,
  update: async (
    companyId: string,
    payload: UpdateCompanyPayload | RuntimeObjectMutationPayload,
  ) =>
    (
      await httpClient.put<Company>(
        `/console/crm/companies/${companyId}`,
        payload,
      )
    ).data,
  delete: async (companyId: string) => {
    await httpClient.delete(`/console/crm/companies/${companyId}`);
  },
};

function normalizeCompanyFieldsResponse(
  response: CompanyFieldsResponse,
): NormalizedCompanyFieldsResponse {
  return {
    object: response.object,
    fields: response.fields.map(
      (field) =>
        ({
          ...field,
          filter: {
            enabled: false,
            operators: [],
            input: inputForFieldType(field.type),
            value_type: valueTypeForFieldType(field.type),
            options: field.options,
          },
          sort: {
            enabled: false,
          },
        }) satisfies RuntimeFieldDescription,
    ),
  };
}

function inputForFieldType(type: string): string {
  if (type === "datetime") {
    return "datetime";
  }

  if (type === "select" || type === "multiselect") {
    return type;
  }

  return "text";
}

function valueTypeForFieldType(type: string): string {
  if (type === "datetime") {
    return "datetime";
  }

  if (type === "multiselect") {
    return "string[]";
  }

  return "string";
}
