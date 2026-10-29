<script lang="ts">
export const description = "An inset sidebar with secondary navigation.";
export const iframeHeight = "800px";
</script>

<script setup lang="ts">
import { onMounted } from "vue";
import { useTenantStore } from "@/app/stores/tenant";
import { Separator } from "@/components/ui/separator";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import WorkspaceSidebar from "./components/WorkspaceSidebar.vue";

const tenantStore = useTenantStore();
onMounted(() => {
  if (!tenantStore.tenant && !tenantStore.isResolvingTenant) {
    void tenantStore.resolveTenant();
  }
});
</script>

<template>
  <SidebarProvider>
    <WorkspaceSidebar />
    <SidebarInset
      class="h-svh min-h-0 overflow-hidden md:h-[calc(100svh-1rem)]"
    >
      <header class="flex h-16 min-w-0 shrink-0 items-center gap-2">
        <div class="flex w-full min-w-0 items-center gap-2 px-4">
          <SidebarTrigger class="-ml-1 shrink-0" />
          <Separator
            orientation="vertical"
            class="mr-2 shrink-0 data-[orientation=vertical]:h-4"
          />
          <div
            id="workspace-page-header"
            class="flex min-w-0 flex-1 items-center"
          >
            <RouterView name="header" />
          </div>
        </div>
      </header>
      <div class="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden p-4 pt-0">
        <RouterView />
      </div>
    </SidebarInset>
  </SidebarProvider>
</template>
