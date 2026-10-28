<script setup lang="ts">
import { watch } from "vue";
import { useRoute } from "vue-router";

import { exampleNavigation } from "@/app/navigation";
import type { SidebarProps } from "@/components/ui/sidebar";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  useSidebar,
} from "@/components/ui/sidebar";
import ConsoleNavUser from "@/layouts/shared/ConsoleNavUser.vue";
import TenantWorkspaceMenu from "@/layouts/shared/TenantWorkspaceMenu.vue";
import ExampleNavMenu from "./ExampleNavMenu.vue";

const props = withDefaults(defineProps<SidebarProps>(), {
  variant: "inset",
});
const route = useRoute();
const { isMobile, setOpenMobile } = useSidebar();

function closeMobileSidebar(): void {
  if (isMobile.value) setOpenMobile(false);
}

watch(() => route.fullPath, closeMobileSidebar);
</script>

<template>
  <Sidebar v-bind="props">
    <SidebarHeader>
      <TenantWorkspaceMenu area="example" />
    </SidebarHeader>
    <SidebarContent>
      <ExampleNavMenu
        :groups="exampleNavigation"
        :active-path="route.path"
        @navigate="closeMobileSidebar"
      />
    </SidebarContent>
    <SidebarFooter>
      <ConsoleNavUser />
    </SidebarFooter>
  </Sidebar>
</template>
