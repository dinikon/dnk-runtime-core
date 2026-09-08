import { defineNuxtRouteMiddleware, navigateTo, useNuxtApp } from "#imports";
import { loginUrl, useCoreSession } from "../modules/session/model/session";

export default defineNuxtRouteMiddleware(async (to) => {
  // The root component checks the session after hydration on a direct visit.
  // This keeps the server's anonymous shell identical to the first client render.
  if (import.meta.server || useNuxtApp().isHydrating) return;
  const { session, refreshSession } = useCoreSession();
  await refreshSession();
  if (!session.value.error && session.value.authenticated === false) {
    return navigateTo(loginUrl(to.fullPath), { external: true });
  }
});
