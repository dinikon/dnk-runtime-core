<script setup lang="ts">
import { Inbox } from "@lucide/vue";
import { toast } from "vue-sonner";

import { EmptyState } from "@/components/custom-ui/empty-state";

const emptyState = {
  title: "No databases added",
  description:
    "Read and write directly to databases and stores from your projects.",
  icon: Inbox,
  primaryActionLabel: "Create new",
  secondaryActionLabel: "Learn more",
};

function handleCreate(): void {
  toast("Create new", {
    description: "Демонстрация основного действия пустого состояния.",
  });
}

function handleLearnMore(): void {
  toast("Learn more", {
    description:
      "Пустое состояние помогает начать работу, когда список ещё пуст.",
  });
}
</script>

<template>
  <section
    aria-label="EmptyState"
    class="flex min-h-0 flex-1 flex-col gap-10 overflow-y-auto pb-4"
  >
    <div class="shrink-0 p-4 sm:p-6">
      <EmptyState
        v-bind="emptyState"
        @primary-action="handleCreate"
        @secondary-action="handleLearnMore"
      />
    </div>
  </section>
</template>
