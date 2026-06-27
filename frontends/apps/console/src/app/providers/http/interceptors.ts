import type { Pinia } from "pinia";
import type { Router } from "vue-router";

import { useUserStore } from "@/app/stores/user";
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
      if (currentRoute.name !== "login") {
        useUserStore(pinia).clearUser();
        void router
          .replace({
            name: "login",
            query: {
              redirect: currentRoute.fullPath,
            },
          })
          .catch(() => undefined);
      }

      return Promise.reject(error);
    },
  );
}
