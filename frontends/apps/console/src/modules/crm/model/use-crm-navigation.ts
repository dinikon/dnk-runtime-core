import { inject, provide, ref, type InjectionKey } from "vue";
import type { CrmKind } from "./crm.types";

export interface CrmPreviewTarget {
  kind: CrmKind;
  id: string;
  key: number;
}

export function crmRecordRoute(kind: CrmKind, id: string) {
  return {
    name: kind === "contacts" ? "crm-contact-detail" : "crm-company-detail",
    params: { id },
  };
}

function createCrmNavigation() {
  const stack = ref<CrmPreviewTarget[]>([]);
  let key = 0;
  function preview(kind: CrmKind, id: string) {
    stack.value.push({ kind, id, key: ++key });
  }
  function closeTop() {
    stack.value.pop();
  }
  function clear() {
    stack.value = [];
  }
  return { stack, preview, closeTop, clear };
}

type CrmNavigation = ReturnType<typeof createCrmNavigation>;
const navigationKey: InjectionKey<CrmNavigation> = Symbol("crm-navigation");

export function provideCrmNavigation() {
  const navigation = createCrmNavigation();
  provide(navigationKey, navigation);
  return navigation;
}

export function useCrmNavigation() {
  const navigation = inject(navigationKey);
  if (!navigation) throw new Error("CRM navigation provider is missing");
  return navigation;
}
