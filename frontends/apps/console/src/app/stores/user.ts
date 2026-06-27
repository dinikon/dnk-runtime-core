import { defineStore } from "pinia";
import { computed, ref } from "vue";

import type { ConsoleUser } from "@/modules/auth/api/auth.contracts";

export const useUserStore = defineStore("user", () => {
  const user = ref<ConsoleUser | null>(null);

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

  function setUser(nextUser: ConsoleUser) {
    user.value = nextUser;
  }

  function clearUser() {
    user.value = null;
  }

  return {
    avatarUrl,
    clearUser,
    displayName,
    initials,
    isAuthenticated,
    primaryEmail,
    setUser,
    user,
  };
});
