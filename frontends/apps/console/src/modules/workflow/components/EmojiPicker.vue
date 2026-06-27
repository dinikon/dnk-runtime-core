<script setup lang="ts">
import { computed, ref } from "vue";
import { Check, Search } from "@lucide/vue";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { allEmojis, emojiCategories } from "@/modules/workflow/model/emoji-data";

const props = defineProps<{
  modelValue: string;
}>();

const emit = defineEmits<{
  (event: "update:modelValue", value: string): void;
}>();

const isOpen = ref(false);
const activeCategoryId = ref("all");
const searchQuery = ref("");

const activeCategory = computed(() =>
  emojiCategories.find((category) => category.id === activeCategoryId.value),
);
const normalizedSearchQuery = computed(() =>
  searchQuery.value.trim().toLowerCase(),
);
const visibleEmojis = computed(() => {
  if (normalizedSearchQuery.value) {
    const matchingCategories = emojiCategories.filter((category) => {
      const categoryText = [category.label, ...category.keywords]
        .join(" ")
        .toLowerCase();

      return categoryText.includes(normalizedSearchQuery.value);
    });

    if (matchingCategories.length > 0) {
      return [...new Set(matchingCategories.flatMap((category) => category.emojis))];
    }

    return allEmojis.filter((emoji) => emoji.includes(searchQuery.value.trim()));
  }

  return activeCategory.value?.emojis ?? allEmojis;
});

function selectEmoji(emoji: string) {
  emit("update:modelValue", emoji);
  isOpen.value = false;
}
</script>

<template>
  <Popover v-model:open="isOpen">
    <PopoverTrigger as-child>
      <Button
        type="button"
        variant="outline"
        class="w-full justify-start"
      >
        <span class="text-lg leading-none">{{ modelValue }}</span>
        <span class="truncate text-muted-foreground">Choose emoji</span>
      </Button>
    </PopoverTrigger>
    <PopoverContent
      align="start"
      class="w-[min(21rem,calc(100vw-2rem))] p-2"
    >
      <div class="grid gap-2">
        <div class="relative">
          <Search
            class="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            v-model="searchQuery"
            class="h-8 pl-8"
            placeholder="Search categories"
            type="search"
          />
        </div>

        <div class="flex gap-1 overflow-x-auto pb-1">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            :class="
              cn(
                'size-8 shrink-0 text-base',
                activeCategoryId === 'all' && 'bg-accent',
              )
            "
            aria-label="All emoji"
            @click="activeCategoryId = 'all'"
          >
            ✨
          </Button>
          <Button
            v-for="category in emojiCategories"
            :key="category.id"
            type="button"
            variant="ghost"
            size="icon"
            :class="
              cn(
                'size-8 shrink-0 text-base',
                activeCategoryId === category.id && 'bg-accent',
              )
            "
            :aria-label="category.label"
            @click="activeCategoryId = category.id"
          >
            {{ category.icon }}
          </Button>
        </div>

        <ScrollArea class="h-56 rounded-md border">
          <div class="grid grid-cols-8 gap-1 p-2">
            <button
              v-for="emoji in visibleEmojis"
              :key="emoji"
              type="button"
              class="relative flex size-8 items-center justify-center rounded-md text-lg transition-colors hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
              :aria-label="`Select ${emoji}`"
              @click="selectEmoji(emoji)"
            >
              <span>{{ emoji }}</span>
              <Check
                v-if="emoji === modelValue"
                class="absolute right-0.5 bottom-0.5 size-3 rounded-full bg-primary text-primary-foreground"
                aria-hidden="true"
              />
            </button>
          </div>
        </ScrollArea>
      </div>
    </PopoverContent>
  </Popover>
</template>
