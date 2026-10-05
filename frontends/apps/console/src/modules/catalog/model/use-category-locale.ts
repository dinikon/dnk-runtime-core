import { computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useLocales } from "./queries";
export function useCategoryLocale() {
  const route = useRoute();
  const router = useRouter();
  const locales = useLocales();
  const locale = computed(() =>
    typeof route.query.locale === "string" ? route.query.locale : "",
  );
  const languages = computed(() =>
    [...(locales.data.value ?? [])].sort((a, b) =>
      a.code.localeCompare(b.code),
    ),
  );
  watch(
    [languages, locale],
    ([values]) => {
      if (!locale.value && values.length)
        void router.replace({
          query: {
            ...route.query,
            locale:
              values.find((item) => item.code === "uk")?.code ??
              values[0]!.code,
          },
        });
    },
    { immediate: true },
  );
  const changeLocale = (value: string) => {
    if (value !== locale.value)
      void router.push({ query: { ...route.query, locale: value } });
  };
  return { locale, locales, languages, changeLocale };
}
