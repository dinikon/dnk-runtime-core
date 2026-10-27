<script setup lang="ts">
import { computed } from "vue";
import { EllipsisVertical } from "@lucide/vue";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { PageHeaderAction } from "./page-header.types";

const props = withDefaults(
  defineProps<{
    actions: readonly PageHeaderAction[];
    withIcons?: boolean;
    compact?: boolean;
  }>(),
  { withIcons: false, compact: false },
);

const emit = defineEmits<{ action: [action: PageHeaderAction] }>();
const mobileActions = computed(() =>
  props.actions
    .filter((action) => action.mobileOrder !== undefined)
    .sort(
      (first, second) => (first.mobileOrder ?? 0) - (second.mobileOrder ?? 0),
    ),
);
const overflowActions = computed(() =>
  props.actions.filter((action) => action.mobileOrder === undefined),
);
</script>

<template>
  <div class="shrink-0" data-slot="page-header-actions">
    <div
      class="hidden items-center gap-2 @2xl/page-header:flex"
      data-slot="desktop-actions"
    >
      <Button
        v-for="action in actions"
        :key="action.id"
        type="button"
        :variant="action.variant"
        :disabled="action.disabled"
        @click="emit('action', action)"
      >
        <component
          :is="action.icon"
          v-if="withIcons && action.icon"
          data-icon="inline-start"
        />
        {{ action.label }}
      </Button>
    </div>
    <div
      class="flex items-center gap-2 @2xl/page-header:hidden"
      data-slot="mobile-actions"
    >
      <Button
        v-for="action in mobileActions"
        :key="action.id"
        type="button"
        :variant="action.variant"
        :disabled="action.disabled"
        @click="emit('action', action)"
      >
        <component
          :is="action.icon"
          v-if="withIcons && action.icon"
          data-icon="inline-start"
        />
        {{ action.label }}
      </Button>
      <DropdownMenu v-if="overflowActions.length">
        <DropdownMenuTrigger as-child>
          <Button
            type="button"
            :variant="compact ? 'ghost' : 'outline'"
            size="icon"
            aria-label="More actions"
          >
            <EllipsisVertical />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuGroup>
            <DropdownMenuItem
              v-for="action in overflowActions"
              :key="action.id"
              :disabled="action.disabled"
              @select="emit('action', action)"
            >
              <component :is="action.icon" v-if="withIcons && action.icon" />
              {{ action.label }}
            </DropdownMenuItem>
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  </div>
</template>
