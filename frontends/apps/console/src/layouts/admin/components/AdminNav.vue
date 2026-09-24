<script setup lang="ts">
import { ChevronRight } from "@lucide/vue";
import { computed } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import type { AdminNavigationGroup } from "@/app/navigation";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from "@/components/ui/sidebar";

const props = defineProps<{
  groups: AdminNavigationGroup[];
}>();

const route = useRoute();
const router = useRouter();
const visibleGroups = computed(() =>
  props.groups
    .filter((group) => !group.hidden)
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => !item.hidden),
    }))
    .filter((group) => group.items.length > 0),
);

function isActive(url?: string) {
  if (!url) return false;
  const target = router.resolve(url);
  if (target.path !== route.path) return false;
  const tab = target.query.tab;
  if (typeof tab === "string") {
    return (route.query.tab ?? "members") === tab;
  }
  return true;
}
</script>

<template>
  <SidebarGroup v-for="group in visibleGroups" :key="group.title">
    <SidebarGroupLabel>{{ group.title }}</SidebarGroupLabel>
    <SidebarMenu>
      <Collapsible
        v-for="item in group.items"
        :key="item.title"
        as-child
        :default-open="item.defaultOpen || isActive(item.url)"
      >
        <SidebarMenuItem>
          <SidebarMenuButton
            v-if="item.disabled || !item.url"
            :disabled="item.disabled"
            :tooltip="item.title"
          >
            <component :is="item.icon" v-if="item.icon" />
            <span>{{ item.title }}</span>
          </SidebarMenuButton>
          <SidebarMenuButton
            v-else
            as-child
            :is-active="isActive(item.url)"
            :tooltip="item.title"
          >
            <RouterLink :to="item.url">
              <component :is="item.icon" v-if="item.icon" />
              <span>{{ item.title }}</span>
            </RouterLink>
          </SidebarMenuButton>
          <template v-if="item.items?.length">
            <CollapsibleTrigger as-child>
              <SidebarMenuAction class="data-[state=open]:rotate-90">
                <ChevronRight />
                <span class="sr-only">Открыть {{ item.title }}</span>
              </SidebarMenuAction>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <SidebarMenuSub>
                <SidebarMenuSubItem
                  v-for="child in item.items.filter((entry) => !entry.hidden)"
                  :key="child.title"
                >
                  <SidebarMenuSubButton
                    v-if="child.disabled || !child.url"
                    :aria-disabled="child.disabled"
                  >
                    <span>{{ child.title }}</span>
                  </SidebarMenuSubButton>
                  <SidebarMenuSubButton
                    v-else
                    as-child
                    :is-active="isActive(child.url)"
                  >
                    <RouterLink :to="child.url">
                      <span>{{ child.title }}</span>
                    </RouterLink>
                  </SidebarMenuSubButton>
                </SidebarMenuSubItem>
              </SidebarMenuSub>
            </CollapsibleContent>
          </template>
        </SidebarMenuItem>
      </Collapsible>
    </SidebarMenu>
  </SidebarGroup>
</template>
