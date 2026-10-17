<script setup lang="ts">
import { RouterLink } from "vue-router";
import type { CrmKind } from "../../model/crm.types";
import {
  crmRecordRoute,
  useCrmNavigation,
} from "../../model/use-crm-navigation";

const props = defineProps<{ kind: CrmKind; id: string }>();
const navigation = useCrmNavigation();

function open(event: MouseEvent) {
  if (
    event.button !== 0 ||
    event.metaKey ||
    event.ctrlKey ||
    event.shiftKey ||
    event.altKey
  )
    return;
  event.preventDefault();
  navigation.preview(props.kind, props.id);
}
</script>

<template>
  <RouterLink :to="crmRecordRoute(kind, id)" custom v-slot="{ href }">
    <a :href="href" @click="open"><slot /></a>
  </RouterLink>
</template>
