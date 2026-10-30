<script setup lang="ts">
import { ref, watch } from "vue";
import { ChevronDown } from "@lucide/vue";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
const props = withDefaults(
  defineProps<{ title: string; defaultOpen?: boolean; reveal?: number }>(),
  { defaultOpen: true },
);
const open = ref(props.defaultOpen);
watch(
  () => props.reveal,
  () => {
    open.value = true;
  },
);
</script>
<template>
  <Collapsible v-model:open="open" as="section" class="border-b py-3">
    <CollapsibleTrigger
      class="group flex min-h-11 w-full items-center justify-between gap-3 text-left"
    >
      <span role="heading" aria-level="2" class="text-sm font-semibold">{{
        title
      }}</span
      ><ChevronDown
        class="size-4 shrink-0 transition-transform group-data-[state=open]:rotate-180"
      />
    </CollapsibleTrigger>
    <CollapsibleContent force-mount v-show="open" class="pt-2"
      ><slot
    /></CollapsibleContent>
  </Collapsible>
</template>
