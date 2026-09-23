import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { authApi } from "@/modules/auth/api/auth.api";
import type { ConsoleUser } from "@/modules/auth/api/auth.contracts";

export type SessionStatus = "idle" | "loading" | "ready" | "error";

export const useUserStore = defineStore("user", () => {
  const user = ref<ConsoleUser | null>(null);
  const sessionStatus = ref<SessionStatus>("idle");
  let sessionPromise: Promise<ConsoleUser> | null = null;

  const primaryEmail = computed(
    () => user.value?.emails.find((email) => email.is_primary)?.email ?? null,
  );
  const displayName = computed(() => {
    if (!user.value) {
      return primaryEmail.value ?? "User";
    }

    const fullName = [user.value.first_name, user.value.last_name]
      .map((part) => part.trim())
      .filter(Boolean)
      .join(" ");

    return fullName || primaryEmail.value || "User";
  });
  const avatarUrl = computed(() => user.value?.avatar ?? "");
  const initials = computed(() => {
    const source =
      displayName.value === "User"
        ? (primaryEmail.value ?? displayName.value)
        : displayName.value;
    const parts = source
      .replace(/@.*/, "")
      .split(/[\s._-]+/)
      .map((part) => part.trim())
      .filter(Boolean);

    return (
      parts
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase())
        .join("") || "U"
    );
  });
  const isAuthenticated = computed(() => user.value !== null);
  const isAdmin = computed(() => user.value?.role === "admin");

  function setUser(nextUser: ConsoleUser) {
    user.value = nextUser;
    sessionStatus.value = "ready";
  }

  function clearUser() {
    user.value = null;
    sessionStatus.value = "idle";
    sessionPromise = null;
  }

  async function ensureCurrentUser() {
    if (user.value && sessionStatus.value === "ready") {
      return user.value;
    }

    if (sessionPromise) {
      return sessionPromise;
    }

    sessionStatus.value = "loading";
    sessionPromise = authApi
      .getCurrentUser()
      .then((currentUser) => {
        setUser(currentUser);
        return currentUser;
      })
      .catch((error: unknown) => {
        user.value = null;
        sessionStatus.value = "error";
        throw error;
      })
      .finally(() => {
        sessionPromise = null;
      });

    return sessionPromise;
  }

  return {
    avatarUrl,
    clearUser,
    displayName,
    ensureCurrentUser,
    initials,
    isAdmin,
    isAuthenticated,
    primaryEmail,
    sessionStatus,
    setUser,
    user,
  };
});
