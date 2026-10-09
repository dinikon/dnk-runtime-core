import { computed, watch, onBeforeUnmount } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useTenantStore } from "@/app/stores/tenant";
import { useUserStore } from "@/app/stores/user";
import { catalogApi } from "../api/catalog.api";
import type { LocaleOption } from "./catalog.types";
export function useCatalogContext(
  dirty: () => boolean = () => false,
  pending: () => boolean = () => false,
  clear: () => void = () => {},
) {
  const route = useRoute(),
    router = useRouter(),
    tenant = useTenantStore(),
    user = useUserStore(),
    cache = useQueryClient();
  const tenantId = computed(() => tenant.tenant?.tenant_id ?? "");
  const sessionKey = computed(() => `${tenantId.value}:${user.user?.id ?? ""}`);
  const locale = computed(() =>
    typeof route.query.locale === "string" ? route.query.locale : "",
  );
  const locales = useQuery({
    queryKey: computed(() => [
      "catalog",
      tenantId.value,
      sessionKey.value,
      "locales",
    ]),
    queryFn: ({ signal }) => catalogApi.locales(signal),
    select: (items) => items.map((i) => ({ ...i, active: true })),
    enabled: computed(() => !!tenantId.value),
  });
  const options = computed<LocaleOption[]>(() => {
    const all = locales.data.value ?? [];
    return locale.value && !all.some((i) => i.code === locale.value)
      ? [
          ...all,
          {
            code: locale.value,
            name:
              locale.value +
              (locales.isPending.value ? " (проверка…)" : " (неактивна)"),
            active: false,
          },
        ]
      : all;
  });
  const active = computed(
    () => locales.data.value?.some((i) => i.code === locale.value) ?? false,
  );
  function canLeave() {
    if (pending()) return false;
    return (
      !dirty() ||
      window.confirm("Есть несохранённые изменения. Отказаться от них?")
    );
  }
  onBeforeRouteLeave(canLeave);
  onBeforeRouteUpdate(
    (to, from) => to.fullPath === from.fullPath || canLeave(),
  );
  let mounted = true;
  function captureSession() {
    const captured = sessionKey.value;
    return () => mounted && sessionKey.value === captured;
  }
  const beforeUnload = (event: BeforeUnloadEvent) => {
    if (dirty() || pending()) {
      event.preventDefault();
      event.returnValue = "";
    }
  };
  window.addEventListener("beforeunload", beforeUnload);
  onBeforeUnmount(() => {
    mounted = false;
    window.removeEventListener("beforeunload", beforeUnload);
  });
  watch(
    () => [tenantId.value, user.user?.id],
    (_next, previous) => {
      if (previous[0]) {
        void cache.cancelQueries({ queryKey: ["catalog", previous[0]] });
        cache.removeQueries({ queryKey: ["catalog", previous[0]] });
      }
      clear();
    },
  );
  const key = (scenario: string, ...parts: unknown[]) => [
    "catalog",
    tenantId.value,
    sessionKey.value,
    scenario,
    ...parts,
    locale.value,
  ];
  function selectLocale(value: string) {
    void router.replace({
      query: { ...route.query, locale: value || undefined, page: undefined },
    });
  }
  return {
    route,
    router,
    tenantId,
    sessionKey,
    locale,
    locales,
    options,
    active,
    key,
    selectLocale,
    captureSession,
  };
}
