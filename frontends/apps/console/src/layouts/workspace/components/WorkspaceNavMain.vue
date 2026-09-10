<script setup lang="ts">
import type { WorkspaceNavigationGroup } from "@/app/navigation";
import { ChevronRight } from "@lucide/vue";
import { RouterLink } from "vue-router";

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

defineProps<{
  groups: WorkspaceNavigationGroup[];
}>();
</script>

<template>
  <SidebarGroup v-for="group in groups" :key="group.title">
    <SidebarGroupLabel>{{ group.title }}</SidebarGroupLabel>
    <SidebarMenu>
      <Collapsible
        v-for="item in group.items"
        :key="item.title"
        as-child
        :default-open="item.defaultOpen"
      >
        <SidebarMenuItem>
          <SidebarMenuButton as-child :tooltip="item.title">
            <a
              v-if="item.external"
              :href="item.url"
              target="_blank"
              rel="noopener noreferrer"
            >
              <component :is="item.icon" />
              <span>{{ item.title }}</span>
            </a>
            <RouterLink v-else :to="item.url">
              <component :is="item.icon" />
              <span>{{ item.title }}</span>
            </RouterLink>
          </SidebarMenuButton>
          <template v-if="item.items?.length">
            <CollapsibleTrigger as-child>
              <SidebarMenuAction class="data-[state=open]:rotate-90">
                <ChevronRight />
                <span class="sr-only">Toggle {{ item.title }}</span>
              </SidebarMenuAction>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <SidebarMenuSub>
                <SidebarMenuSubItem
                  v-for="subItem in item.items"
                  :key="subItem.title"
                >
                  <SidebarMenuSubButton as-child>
                    <a
                      v-if="subItem.external"
                      :href="subItem.url"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <component :is="subItem.icon" />
                      <span>{{ subItem.title }}</span>
                    </a>
                    <RouterLink v-else :to="subItem.url">
                      <component :is="subItem.icon" />
                      <span>{{ subItem.title }}</span>
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
