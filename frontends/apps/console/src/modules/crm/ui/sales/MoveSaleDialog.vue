<script setup lang="ts">
import { ref, watch, useId } from "vue";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/native-select";
import { Field, FieldLabel } from "@/components/ui/field";
import type { Funnel, FunnelStage } from "@/modules/funnel";
const props = defineProps<{
  open: boolean;
  transfer?: boolean;
  title: string;
  currentId: string;
  stages: FunnelStage[];
  funnels: Funnel[];
  pending: boolean;
}>();
const emit = defineEmits<{
  "update:open": [open: boolean];
  submit: [id: string];
}>();
const selected = ref(""),
  id = useId();
watch(
  () => props.open,
  () => (selected.value = ""),
);
</script>
<template>
  <Dialog :open="open" @update:open="!pending && emit('update:open', $event)"
    ><DialogContent :show-close-button="!pending"
      ><form
        class="flex flex-col gap-4"
        @submit.prevent="selected && emit('submit', selected)"
      >
        <DialogHeader
          ><DialogTitle>{{
            transfer ? "Сменить воронку" : "Переместить карточку"
          }}</DialogTitle
          ><DialogDescription
            >{{ title
            }}<template v-if="transfer">
              — карточка перейдёт в первую стадию выбранной воронки.</template
            ></DialogDescription
          ></DialogHeader
        ><Field
          ><FieldLabel :for="id">{{
            transfer ? "Новая воронка" : "Новая стадия"
          }}</FieldLabel
          ><NativeSelect
            :id="id"
            v-model="selected"
            required
            :disabled="pending"
            ><option value="" disabled>Выберите</option>
            <template v-if="transfer"
              ><option
                v-for="f in funnels.filter((v) => v.id !== currentId)"
                :key="f.id"
                :value="f.id"
              >
                {{ f.name }} → {{ f.stages[0]?.name }}
              </option></template
            ><template v-else
              ><option
                v-for="s in stages.filter((v) => v.id !== currentId)"
                :key="s.id"
                :value="s.id"
              >
                {{ s.name }}
              </option></template
            ></NativeSelect
          ></Field
        ><DialogFooter
          ><Button
            type="button"
            variant="outline"
            :disabled="pending"
            @click="emit('update:open', false)"
            >Отмена</Button
          ><Button type="submit" :disabled="pending || !selected">{{
            pending ? "Перемещаем…" : "Переместить"
          }}</Button></DialogFooter
        >
      </form></DialogContent
    ></Dialog
  >
</template>
