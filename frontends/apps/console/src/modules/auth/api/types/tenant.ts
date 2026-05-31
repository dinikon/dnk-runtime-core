export interface ResolveTenantResponse {
  exists: boolean;
  available: boolean;
  status: string;
  tenant_id: string | null;
  api_host: string | null;
}
