<script setup lang="ts">
import { FileText, Image, Video, File } from "@lucide/vue";
import type { FileItem } from "../model/types";
defineProps<{ file: FileItem }>();
const icons = {
  documents: FileText,
  images: Image,
  videos: Video,
  other: File,
};
</script>
<template>
  <div class="flex min-w-0 items-center gap-3">
    <component
      :is="icons[file.category]"
      class="size-5 shrink-0 text-muted-foreground"
    />
    <div class="min-w-0">
      <p class="truncate font-medium" :title="file.name">{{ file.name }}</p>
      <p
        class="truncate text-xs text-muted-foreground"
        :title="file.content_type"
      >
        {{ file.content_type }}
      </p>
    </div>
  </div>
</template>
