<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ChevronDown, CircleAlert } from "@lucide/vue";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
const props = defineProps<{
  id: string;
  title: string;
  summary?: string;
  collapsible?: boolean;
  defaultOpen?: boolean;
  dirty?: boolean;
  error?: string;
  reveal?: number;
}>();
const open = ref(!props.collapsible || props.defaultOpen === true);
watch(
  () => [props.error, props.reveal] as const,
  ([error, reveal], previous) => {
    if (error || (reveal && reveal !== previous?.[1])) open.value = true;
  },
  { immediate: true },
);
const headingId = computed(() => `${props.id}-heading`);
</script>
<template>
  <Collapsible
    :id="id"
    v-model:open="open"
    as="section"
    class="product-editor-section"
    :aria-labelledby="headingId"
  >
    <div class="flex min-w-0 items-start justify-between gap-3">
      <CollapsibleTrigger
        v-if="collapsible"
        class="group flex min-h-11 min-w-0 flex-1 items-center justify-between gap-3 text-left"
      >
        <span class="flex min-w-0 flex-col gap-1"
          ><span
            :id="headingId"
            role="heading"
            aria-level="2"
            class="text-lg font-semibold"
            >{{ title }}</span
          ><span
            v-if="summary"
            class="break-words text-sm text-muted-foreground"
            >{{ summary }}</span
          ></span
        ><ChevronDown
          class="size-4 shrink-0 transition-transform group-data-[state=open]:rotate-180"
        />
      </CollapsibleTrigger>
      <div v-else class="flex min-w-0 flex-col gap-1">
        <h2 :id="headingId" class="text-lg font-semibold">{{ title }}</h2>
        <p v-if="summary" class="text-sm text-muted-foreground">
          {{ summary }}
        </p>
      </div>
      <Badge v-if="error" variant="destructive" class="shrink-0"
        ><CircleAlert data-icon="inline-start" />Ошибка</Badge
      ><Badge v-else-if="dirty" variant="outline" class="shrink-0"
        >Изменения</Badge
      >
    </div>
    <CollapsibleContent force-mount v-show="open" class="pt-5"
      ><slot
    /></CollapsibleContent>
  </Collapsible>
</template>
