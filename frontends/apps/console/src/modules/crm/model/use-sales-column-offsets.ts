import { ref, type Ref } from "vue";
import { onBeforeRouteLeave } from "vue-router";
const depths = new Map<string, Record<string, number>>();
export function useSalesColumnOffsets(
  key: () => string,
): Ref<Record<string, number>> {
  const value = ref({ ...depths.get(key()) });
  onBeforeRouteLeave(() => {
    depths.set(key(), { ...value.value });
    if (depths.size > 100) depths.delete(depths.keys().next().value!);
  });
  return value;
}
