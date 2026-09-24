<script setup lang="ts">
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { UsersTab } from "../../model/access.types";

defineProps<{
  modelValue: UsersTab;
  memberCount: number;
  pendingInvitationCount: number;
}>();
const emit = defineEmits<{
  "update:modelValue": [value: UsersTab];
}>();
</script>

<template>
  <Tabs
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event as UsersTab)"
  >
    <TabsList
      class="h-auto w-full justify-start gap-5 rounded-none border-b bg-transparent p-0"
    >
      <TabsTrigger
        value="members"
        class="flex-none rounded-none border-0 border-b-2 border-transparent bg-transparent px-1 pb-3 shadow-none data-[state=active]:border-foreground data-[state=active]:bg-transparent data-[state=active]:shadow-none dark:data-[state=active]:bg-transparent"
      >
        Участники
        <Badge variant="secondary">{{ memberCount }}</Badge>
      </TabsTrigger>
      <TabsTrigger
        value="invitations"
        class="flex-none rounded-none border-0 border-b-2 border-transparent bg-transparent px-1 pb-3 shadow-none data-[state=active]:border-foreground data-[state=active]:bg-transparent data-[state=active]:shadow-none dark:data-[state=active]:bg-transparent"
      >
        Приглашения
        <Badge variant="secondary">{{ pendingInvitationCount }}</Badge>
      </TabsTrigger>
    </TabsList>
  </Tabs>
</template>
