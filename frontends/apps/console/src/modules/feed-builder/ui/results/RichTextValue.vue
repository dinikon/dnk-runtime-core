<script setup lang="ts">
import { computed } from "vue";
import { safeRichTextHtml } from "../../model/rich-text";

const props = defineProps<{ value: string; showSource?: boolean }>();
const safeHtml = computed(() => safeRichTextHtml(props.value));
</script>

<template>
  <div class="min-w-0 whitespace-normal break-words">
    <!-- eslint-disable-next-line vue/no-v-html -- DOMPurify limits the markup before rendering. -->
    <div class="rich-text" v-html="safeHtml" />
    <details v-if="showSource" class="mt-2 text-xs">
      <summary class="cursor-pointer text-muted-foreground">Исходный HTML</summary>
      <pre class="mt-1 whitespace-pre-wrap break-all">{{ value }}</pre>
    </details>
  </div>
</template>

<style scoped>
.rich-text :deep(p + p) { margin-top: 0.5em; }
.rich-text :deep(ul) { padding-inline-start: 1.5em; list-style: disc; }
.rich-text :deep(ol) { padding-inline-start: 1.5em; list-style: decimal; }
.rich-text :deep(h2) { font-size: 1.125em; font-weight: 600; }
.rich-text :deep(h3) { font-weight: 600; }
.rich-text :deep(a) { text-decoration: underline; }
.rich-text :deep(blockquote) { border-inline-start: 2px solid var(--border); padding-inline-start: 0.75em; }
.rich-text :deep(pre) { white-space: pre-wrap; }
</style>
