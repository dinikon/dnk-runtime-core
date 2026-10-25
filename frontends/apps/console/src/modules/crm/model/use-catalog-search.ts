import { ref, watch, onScopeDispose, type Ref } from "vue";
export function useCatalogSearch(): {
  input: Ref<string>;
  search: Ref<string>;
} {
  const input = ref(""),
    search = ref("");
  let timer: ReturnType<typeof setTimeout> | undefined;
  watch(input, (value) => {
    clearTimeout(timer);
    timer = setTimeout(() => (search.value = value), 300);
  });
  onScopeDispose(() => clearTimeout(timer));
  return { input, search };
}
