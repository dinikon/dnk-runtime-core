<script setup lang="ts">
import { Image } from "@lucide/vue";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
defineProps<{ src: string | null }>();
</script>

<template>
  <Avatar class="size-12 rounded-md bg-muted" data-slot="publication-thumbnail">
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
