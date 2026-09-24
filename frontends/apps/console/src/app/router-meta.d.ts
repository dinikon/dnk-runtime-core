import "vue-router";

import type { ConsoleUser } from "@/modules/auth/api/auth.contracts";

declare module "vue-router" {
  interface RouteMeta {
    public?: boolean;
    requiresAuth?: boolean;
    requiredRole?: ConsoleUser["role"];
  }
}

export {};
