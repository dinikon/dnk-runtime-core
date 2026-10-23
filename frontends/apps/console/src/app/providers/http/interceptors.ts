import type { Pinia } from "pinia";
import type { Router } from "vue-router";

import { useUserStore } from "@/app/stores/user";
import { requestsCloudLogin, withoutAuthProvider } from "@/modules/auth";
import { httpClient } from "./http-client";

let interceptorsInstalled = false;

export function installHttpInterceptors(router: Router, pinia: Pinia) {
  if (interceptorsInstalled) {
    return;
  }

  interceptorsInstalled = true;

  httpClient.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status !== 401) {
        return Promise.reject(error);
      }

      const currentRoute = router.currentRoute.value;
      // Before the initial navigation, the router guard owns the login redirect.
      if (currentRoute.matched.length && !currentRoute.meta.public) {
        useUserStore(pinia).clearUser();
        void router
          .replace({
            name: "login",
            query: {
              redirect: withoutAuthProvider(currentRoute.fullPath),
              ...(requestsCloudLogin(currentRoute.query.auth_provider)
                ? { auth_provider: "cloud" }
                : {}),
            },
          })
          .catch(() => undefined);
      }

      return Promise.reject(error);
    },
  );
}
