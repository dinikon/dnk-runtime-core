<script setup lang="ts">
import {
  BookOpen,
  CheckSquare,
  ContactRound,
  FileText,
  Settings,
  Store,
  Target,
  Workflow
} from "lucide-vue-next";

const workspaceItems = [
  {label: "Contacts", icon: ContactRound, active: true},
  {label: "Tasks", icon: CheckSquare},
  {label: "Notes", icon: FileText},
  {label: "Opportunities", icon: Target},
  {label: "Workflows", icon: Workflow}
];

const otherItems = [
  {label: "Settings", icon: Settings},
  {label: "Documentation", icon: BookOpen},
  {label: "App store", icon: Store}
];
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
        <button
            v-for="item in workspaceItems"
            :key="item.label"
            type="button"
            class="flex min-h-9 items-center gap-2 rounded-md px-2 text-sm font-medium text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
            :class="item.active ? 'bg-neutral-200/80 text-neutral-900' : ''"
        >
          <component :is="item.icon" class="size-4"/>
          <span class="truncate">{{ item.label }}</span>
        </button>
      </section>

      <section class="grid gap-1">
        <h2 class="px-1 text-xs font-semibold text-neutral-400">Other</h2>
        <button
            v-for="item in otherItems"
            :key="item.label"
            type="button"
            class="flex min-h-9 items-center gap-2 rounded-md px-2 text-sm font-medium text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        >
          <component :is="item.icon" class="size-4"/>
          <span class="truncate">{{ item.label }}</span>
        </button>
      </section>
    </nav>
  </aside>
</template>
