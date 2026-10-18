<script setup lang="ts">
import { onBeforeUnmount, onMounted } from "vue";
import { useRouter } from "vue-router";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  crmRecordRoute,
  useCrmNavigation,
} from "../../model/use-crm-navigation";
import CrmRecordOverview from "./CrmRecordOverview.vue";

const navigation = useCrmNavigation();
const router = useRouter();

function onKeydown(event: KeyboardEvent) {
  if (event.key !== "Escape" || !navigation.stack.value.length) return;
  event.preventDefault();
  event.stopImmediatePropagation();
  navigation.closeTop();
}

function openPage(kind: "contacts" | "companies", id: string) {
  navigation.clear();
  void router.push(crmRecordRoute(kind, id));
}

onMounted(() => window.addEventListener("keydown", onKeydown, true));
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown, true));
</script>

<template>
  <Sheet
    v-for="(target, index) in navigation.stack.value"
    :key="target.key"
    :open="true"
    :modal="index === navigation.stack.value.length - 1"
    @update:open="
      !$event &&
      index === navigation.stack.value.length - 1 &&
      navigation.closeTop()
    "
  >
    <SheetContent side="right" class="w-full overflow-y-auto sm:max-w-xl">
      <SheetHeader>
        <SheetTitle>{{
          target.kind === "contacts" ? "Контакт" : "Компания"
        }}</SheetTitle>
        <SheetDescription>
          Предпросмотр записи. Escape закрывает текущую карточку.
        </SheetDescription>
      </SheetHeader>
      <CrmRecordOverview :kind="target.kind" :id="target.id" />
      <Button
        variant="outline"
        class="self-start"
        @click="openPage(target.kind, target.id)"
      >
        Открыть на странице
      </Button>
    </SheetContent>
  </Sheet>
</template>
