<script setup lang="ts">
import {
  BookOpen,
  CheckSquare,
  ContactRound,
  Database,
  FileText,
  Settings,
  Store,
  Target,
  Workflow
} from "lucide-vue-next";
import {RouterLink, useRoute} from "vue-router";

const route = useRoute();

const workspaceItems = [
  {label: "Objects", icon: Database, to: "/"},
  {label: "Contacts", icon: ContactRound},
  {label: "Tasks", icon: CheckSquare},
  {label: "Notes", icon: FileText},
  {label: "Opportunities", icon: Target},
  {label: "Workflows", icon: Workflow}
];

const otherItems = [
  {label: "Settings", icon: Settings, to: "/settings/profile"},
  {label: "Documentation", icon: BookOpen},
  {label: "App store", icon: Store}
];

function isActive(to?: string): boolean {
  if (!to) {
    return false;
  }

  if (to === "/") {
    return route.path === "/";
  }

  return route.path.startsWith(to);
}
</script>

<template>
  <aside class="flex h-screen w-64 shrink-0 flex-col border-r border-neutral-200 bg-neutral-50/95 px-3 py-4">
    <div class="mb-7 flex items-center gap-2 px-1">
      <div class="grid size-7 place-items-center rounded-md bg-black text-sm font-semibold text-white">d</div>
      <span class="text-base font-semibold text-neutral-900">dNiko</span>
      <span class="ml-auto text-neutral-400">⌄</span>
    </div>

    <nav class="grid gap-6">
      <section class="grid gap-1">
        <h2 class="px-1 text-xs font-semibold text-neutral-400">Workspace</h2>
        <component
            :is="item.to ? RouterLink : 'button'"
            v-for="item in workspaceItems"
            :key="item.label"
            class="flex min-h-9 items-center gap-2 rounded-md px-2 text-sm font-medium text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
            :class="isActive(item.to) ? 'bg-neutral-200/80 text-neutral-900' : ''"
            :to="item.to"
            type="button"
        >
          <component :is="item.icon" class="size-4"/>
          <span class="truncate">{{ item.label }}</span>
        </component>
      </section>

      <section class="grid gap-1">
        <h2 class="px-1 text-xs font-semibold text-neutral-400">Other</h2>
        <component
            :is="item.to ? RouterLink : 'button'"
            v-for="item in otherItems"
            :key="item.label"
            class="flex min-h-9 items-center gap-2 rounded-md px-2 text-sm font-medium text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
            :class="isActive(item.to) ? 'bg-neutral-200/80 text-neutral-900' : ''"
            :to="item.to"
            type="button"
        >
          <component :is="item.icon" class="size-4"/>
          <span class="truncate">{{ item.label }}</span>
        </component>
      </section>
    </nav>
  </aside>
</template>
