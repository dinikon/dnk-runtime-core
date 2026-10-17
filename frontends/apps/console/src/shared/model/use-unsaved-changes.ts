import { onBeforeUnmount, onMounted, type Ref } from "vue";
import { onBeforeRouteLeave, onBeforeRouteUpdate } from "vue-router";
export function useUnsavedChanges(dirty: Ref<boolean>, pending: Ref<boolean>) {
  const allow = () =>
    !pending.value &&
    (!dirty.value || window.confirm("Изменения не сохранены. Покинуть форму?"));
  onBeforeRouteLeave(allow);
  onBeforeRouteUpdate((to, from) => to.fullPath === from.fullPath || allow());
  const beforeUnload = (event: BeforeUnloadEvent) => {
    if (dirty.value || pending.value) {
      event.preventDefault();
      event.returnValue = "";
    }
  };
  onMounted(() => window.addEventListener("beforeunload", beforeUnload));
  onBeforeUnmount(() =>
    window.removeEventListener("beforeunload", beforeUnload),
  );
}
