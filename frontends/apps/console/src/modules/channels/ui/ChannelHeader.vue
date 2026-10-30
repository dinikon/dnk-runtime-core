<script setup lang="ts">
import { Cable, ChevronRight, MoreHorizontal, Trash2 } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
defineProps<{ title: string; removable?: boolean; busy?: boolean }>();
defineEmits<{ back: []; remove: [] }>();
</script>
<template>
  <div class="flex min-w-0 flex-1 items-center justify-between gap-2">
    <nav
      class="flex min-w-0 items-center gap-1"
      aria-label="Навигация подключения"
    >
      <Button
        type="button"
        variant="ghost"
        size="sm"
        class="shrink-0"
        aria-label="Подключения"
        @click="$emit('back')"
        ><Cable data-icon="inline-start" /><span class="hidden sm:inline"
          >Подключения</span
        ></Button
      >
      <ChevronRight
        class="size-4 shrink-0 text-muted-foreground"
        aria-hidden="true"
      /><span class="truncate text-sm" :title="title" aria-current="page">{{
        title
      }}</span>
    </nav>
    <DropdownMenu v-if="removable"
      ><DropdownMenuTrigger as-child
        ><Button
          type="button"
          variant="ghost"
          size="icon-sm"
          :disabled="busy"
          aria-label="Действия с подключением"
          ><MoreHorizontal /></Button></DropdownMenuTrigger
      ><DropdownMenuContent align="end"
        ><DropdownMenuGroup
          ><DropdownMenuItem
            variant="destructive"
            :disabled="busy"
            @select="$emit('remove')"
            ><Trash2 />Удалить подключение</DropdownMenuItem
          ></DropdownMenuGroup
        ></DropdownMenuContent
      ></DropdownMenu
    >
  </div>
</template>
