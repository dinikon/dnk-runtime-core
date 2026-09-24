import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

import type { UsersTab } from "./access.types";

function queryString(value: unknown) {
  return typeof value === "string" ? value : "";
}

export function useUsersPageState() {
  const route = useRoute();
  const router = useRouter();

  async function updateQuery(updates: Record<string, string | undefined>) {
    const query = { ...route.query };
    for (const [key, value] of Object.entries(updates)) {
      if (!value) delete query[key];
      else query[key] = value;
    }
    await router.replace({ query });
  }

  const tab = computed<UsersTab>({
    get: () => (route.query.tab === "invitations" ? "invitations" : "members"),
    set: (value) => {
      void updateQuery({
        tab: value === "members" ? undefined : value,
        status: undefined,
      });
    },
  });
  const search = computed({
    get: () => queryString(route.query.q),
    set: (value: string) => void updateQuery({ q: value.trim() || undefined }),
  });
  const role = computed({
    get: () => queryString(route.query.role) || "all",
    set: (value: string) =>
      void updateQuery({ role: value === "all" ? undefined : value }),
  });
  const status = computed({
    get: () => queryString(route.query.status) || "all",
    set: (value: string) =>
      void updateQuery({ status: value === "all" ? undefined : value }),
  });

  return { role, search, status, tab };
}
