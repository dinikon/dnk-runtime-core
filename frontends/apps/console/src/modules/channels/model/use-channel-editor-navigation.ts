import { onBeforeUnmount, onMounted, type Ref } from "vue";
import { onBeforeRouteLeave, onBeforeRouteUpdate } from "vue-router";

export function useChannelEditorNavigation(
  dirty: Ref<boolean>,
  busy: Ref<boolean>,
  message = "Изменения не сохранены. Покинуть подключение?",
): void {
  const allow = (): boolean =>
    !busy.value && (!dirty.value || window.confirm(message));
  onBeforeRouteLeave(allow);
  onBeforeRouteUpdate((to, from) => to.path === from.path || allow());
  const unload = (event: BeforeUnloadEvent): void => {
    if (dirty.value || busy.value) {
      event.preventDefault();
      event.returnValue = "";
    }
  };
  onMounted(() => window.addEventListener("beforeunload", unload));
  onBeforeUnmount(() => window.removeEventListener("beforeunload", unload));
}
