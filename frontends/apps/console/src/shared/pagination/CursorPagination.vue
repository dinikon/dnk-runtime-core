<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";

import { Button } from "@/components/ui/button";

const props = withDefaults(
  defineProps<{
    hasMore: boolean;
    loading?: boolean;
    disabled?: boolean;
    mode?: "button" | "infinite";
    root?: HTMLElement | null;
    rootMargin?: string;
    loadingText?: string;
    loadMoreText?: string;
    endText?: string;
  }>(),
  {
    loading: false,
    disabled: false,
    mode: "button",
    root: null,
    rootMargin: "240px 0px",
    loadingText: "Loading more",
    loadMoreText: "Load more",
    endText: "All items loaded",
  },
);

const emit = defineEmits<{
  (event: "loadMore"): void;
}>();

const sentinelRef = ref<HTMLElement | null>(null);

let observer: IntersectionObserver | null = null;

const canLoadMore = computed(() => {
  return props.hasMore && !props.loading && !props.disabled;
});

function loadMore() {
  if (!canLoadMore.value) {
    return;
  }

  emit("loadMore");
}

function cleanupObserver() {
  observer?.disconnect();
  observer = null;
}

function setupObserver() {
  cleanupObserver();

  if (props.mode !== "infinite" || !sentinelRef.value || !canLoadMore.value) {
    return;
  }

  observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        loadMore();
      }
    },
    {
      root: props.root ?? null,
      rootMargin: props.rootMargin,
    },
  );

  observer.observe(sentinelRef.value);
}

watch(
  () => [
    props.mode,
    props.root,
    props.rootMargin,
    props.hasMore,
    props.loading,
    props.disabled,
    sentinelRef.value,
  ],
  setupObserver,
  {
    flush: "post",
  },
);

onBeforeUnmount(cleanupObserver);
</script>

<template>
  <div
    ref="sentinelRef"
    class="flex justify-center py-4 text-sm text-muted-foreground"
  >
    <Button
      v-if="mode === 'button' && hasMore"
      type="button"
      variant="outline"
      size="sm"
      :disabled="disabled || loading"
      @click="loadMore"
    >
      {{ loading ? loadingText : loadMoreText }}
    </Button>

    <span v-else-if="loading">
      {{ loadingText }}
    </span>

    <span v-else-if="!hasMore">
      {{ endText }}
    </span>

    <span v-else-if="mode === 'infinite'">
      Scroll for more
    </span>
  </div>
</template>
