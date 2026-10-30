<script setup lang="ts">
import { Image } from "@lucide/vue";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
defineProps<{ src: string | null; compact?: boolean }>();
</script>

<template>
  <Avatar
    :class="cn('shrink-0 rounded-md bg-muted', compact ? 'size-7' : 'size-12')"
    data-slot="publication-thumbnail"
  >
    <AvatarImage
      v-if="src"
      :key="src"
      :src="src"
      alt=""
      class="object-contain"
    />
    <AvatarFallback class="rounded-md text-muted-foreground"
      ><Image aria-hidden="true"
    /></AvatarFallback>
  </Avatar>
</template>
