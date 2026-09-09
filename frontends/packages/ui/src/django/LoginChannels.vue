<script setup lang="ts">
import { nextTick, onMounted, ref } from "vue";
import { ToggleGroup, ToggleGroupItem } from "@dnk/ui/components/toggle-group";

const props = defineProps<{
  channels: { value: string; label: string; href: string; panelId: string }[];
  initial: string;
  focused?: string;
}>();
const selected = ref(props.initial);

function selectChannel(value: unknown) {
  const channel = props.channels.find(item => item.value === value);
  if (!channel) return; // The selected segment cannot be toggled off.
  selected.value = channel.value;
  for (const item of props.channels) {
    const panel = document.getElementById(item.panelId);
    if (panel) panel.hidden = item.value !== channel.value;
  }
  // Only presentation changes: fields stay mounted and no request is issued.
  history.replaceState(history.state, "", channel.href);
}

onMounted(async () => {
  if (props.focused) {
    await nextTick();
    document.getElementById(`channel-${props.focused}`)?.focus();
  }
});
</script>

<template>
  <ToggleGroup class="auth-channel-group" type="single" :spacing="1" :model-value="selected" aria-label="Способ входа" @update:model-value="selectChannel">
    <ToggleGroupItem v-for="channel in channels" :id="`channel-${channel.value}`" :key="channel.value" :value="channel.value" :aria-controls="channel.panelId">
      {{ channel.label }}
    </ToggleGroupItem>
  </ToggleGroup>
</template>
