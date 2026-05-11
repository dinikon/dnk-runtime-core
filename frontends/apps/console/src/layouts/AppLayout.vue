<script setup lang="ts">
import AppSidebar from "@/layouts/default/components/AppSidebar.vue";
import {Separator} from "@/components/ui/separator";
import {SidebarInset, SidebarProvider, SidebarTrigger} from "@/components/ui/sidebar";
</script>

<template>
  <SidebarProvider class="h-svh max-h-svh overflow-hidden">
    <AppSidebar/>

    <SidebarInset class="min-h-0 overflow-hidden">
      <header class="flex h-16 shrink-0 items-center gap-2 border-b border-border px-4">
        <SidebarTrigger class="-ml-1"/>
        <Separator orientation="vertical" class="mr-2 data-[orientation=vertical]:h-4"/>
        <div class="min-w-0 flex-1">
          <slot name="header"/>
        </div>
      </header>

      <div class="flex min-h-0 flex-1 flex-col gap-3 overflow-auto p-4">
        <slot/>
      </div>
    </SidebarInset>
  </SidebarProvider>
</template>
