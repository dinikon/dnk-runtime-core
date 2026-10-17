<script setup lang="ts">
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
defineEmits<{ select: [id: EditorGroup] }>();
</script>
<template>
  <DropdownMenu
    ><DropdownMenuTrigger as-child
      ><Button
        type="button"
        variant="outline"
        class="min-h-11"
        aria-label="Разделы товара"
        ><List data-icon="inline-start" /><span class="hidden sm:inline"
          >Разделы</span
        ></Button
      ></DropdownMenuTrigger
    ><DropdownMenuContent align="start"
      ><DropdownMenuGroup
        ><DropdownMenuItem
          v-for="group in editorGroups"
          :key="group.id"
          class="min-h-11"
          @select="$emit('select', group.id)"
          >{{ group.title }}</DropdownMenuItem
        ></DropdownMenuGroup
      ></DropdownMenuContent
    ></DropdownMenu
  >
</template>
