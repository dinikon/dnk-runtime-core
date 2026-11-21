<script setup lang="ts">
import { ref } from "vue";
import { List } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  editorGroups,
  type EditorGroup,
} from "../../model/product-editor-layout";
const emit = defineEmits<{ select: [id: EditorGroup] }>();
defineProps<{ compact?: boolean; groups?: readonly EditorGroup[] }>();
const navigating = ref(false);
function select(id: EditorGroup): void {
  navigating.value = true;
  emit("select", id);
}
function close(event: Event): void {
  if (navigating.value) event.preventDefault();
  navigating.value = false;
}
</script>
<template>
  <DropdownMenu
    ><DropdownMenuTrigger as-child
      ><Button
        type="button"
        :variant="compact ? 'ghost' : 'outline'"
        :size="compact ? 'icon' : 'default'"
        class="min-h-11"
        aria-label="Разделы товара"
        ><List data-icon="inline-start" /><span
          v-if="!compact"
          class="hidden sm:inline"
          >Разделы</span
        ></Button
      ></DropdownMenuTrigger
    ><DropdownMenuContent align="start" @close-auto-focus="close"
      ><DropdownMenuGroup
        ><DropdownMenuItem
          v-for="group in editorGroups.filter(
            (group) => !groups || groups.includes(group.id),
          )"
          :key="group.id"
          class="min-h-11"
          @select="select(group.id)"
          >{{ group.title }}</DropdownMenuItem
        ></DropdownMenuGroup
      ></DropdownMenuContent
    ></DropdownMenu
  >
</template>
