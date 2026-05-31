import { defineStore } from "pinia";

import { getApiErrorStatus } from "@/app/providers/http";
import { authApi } from "@/modules/auth/api/auth.api";
import type { AuthTenantState } from "@/modules/auth/model/auth.types";

export const useTenantStore = defineStore("tenant", {
  state: (): AuthTenantState => ({
    tenant: null,
    isResolvingTenant: false,
  }),
  getters: {
    isTenantAvailable: (state) =>
      state.tenant?.exists === true && state.tenant.available === true,
    tenantName: (state) => state.tenant?.tenant_name ?? "Workspace",
    tenantStatus: (state) => state.tenant?.status ?? "unknown",
  },
  actions: {
    async resolveTenant() {
      this.isResolvingTenant = true;

      try {
        this.tenant = await authApi.resolveTenant();
      } catch (error) {
        const status = getApiErrorStatus(error);
        this.tenant = {
          exists: false,
          available: false,
          status: status ? `http_${status}` : "unknown_error",
          tenant_id: null,
          tenant_name: null,
          api_host: null,
        };
      } finally {
        this.isResolvingTenant = false;
      }
    },
  },
});
