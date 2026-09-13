import axios from "axios";

import { apiBaseUrl } from "@/shared/config/env";

export const httpClient = axios.create({
  baseURL: apiBaseUrl,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// Fetch after session transitions too: a pre-login token cannot authorize a
// mutation in the newly created local session. GET requests never recurse.
httpClient.interceptors.request.use(async (config) => {
  if (["post", "put", "patch", "delete"].includes(config.method ?? "")) {
    const { data } = await httpClient.get<{ csrf_token: string }>(
      "/console/auth/csrf",
    );
    config.headers.set("X-CSRF-Token", data.csrf_token);
  }
  return config;
});
