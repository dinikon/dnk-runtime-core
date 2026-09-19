<script setup lang="ts">
import { ArrowLeft, Loader2 } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

defineProps<{ nextRuns: string[]; scheduleError: string; busy: boolean; editMode: boolean }>();
defineEmits<{ back: []; submit: [] }>();
const cronExpression = defineModel<string>("cronExpression", { required: true });
const timezone = defineModel<string>("timezone", { required: true });
const newItemPolicy = defineModel<"create" | "quarantine" | "ignore">("newItemPolicy", { required: true });
const missingPolicy = defineModel<"mark_out_of_stock" | "mark_missing" | "archive" | "keep_last">("missingPolicy", { required: true });
const missingThreshold = defineModel<number>("missingThreshold", { required: true });
</script>

<template>
  <form class="flex flex-col gap-5" @submit.prevent="$emit('submit')">
    <Card>
      <CardHeader><CardTitle>Расписание и обработка позиций</CardTitle></CardHeader>
      <CardContent>
        <FieldGroup class="grid md:grid-cols-2">
          <Field><FieldLabel for="cron">CRON</FieldLabel><Input id="cron" v-model="cronExpression" required /><FieldDescription>Например, 0 */6 * * * — каждые 6 часов.</FieldDescription></Field>
          <Field><FieldLabel for="timezone">Часовой пояс</FieldLabel><Input id="timezone" v-model="timezone" required /></Field>
          <Field><FieldLabel>Если появилась новая позиция</FieldLabel><Select v-model="newItemPolicy"><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="create">Создать оффер</SelectItem><SelectItem value="quarantine">На проверку</SelectItem><SelectItem value="ignore">Игнорировать</SelectItem></SelectGroup></SelectContent></Select></Field>
          <Field><FieldLabel>Если позиция исчезла</FieldLabel><Select v-model="missingPolicy"><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="mark_out_of_stock">Установить «Нет в наличии»</SelectItem><SelectItem value="mark_missing">Отметить отсутствующей</SelectItem><SelectItem value="archive">Архивировать</SelectItem><SelectItem value="keep_last">Оставить без изменений</SelectItem></SelectGroup></SelectContent></Select></Field>
          <Field><FieldLabel for="threshold">После скольких загрузок</FieldLabel><Input id="threshold" v-model.number="missingThreshold" type="number" min="1" max="100" /></Field>
          <div class="rounded-lg border bg-muted/30 p-3 md:col-span-2"><p class="text-sm font-medium">Следующие запуски</p><p v-if="scheduleError" class="mt-2 text-sm text-destructive">{{ scheduleError }}</p><ol v-else class="mt-2 grid gap-1 text-sm text-muted-foreground"><li v-for="run in nextRuns" :key="run">{{ new Date(run).toLocaleString('uk-UA', { timeZone: timezone }) }}</li></ol></div>
        </FieldGroup>
      </CardContent>
    </Card>
    <div class="flex justify-between"><Button type="button" variant="outline" @click="$emit('back')"><ArrowLeft data-icon="inline-start" />Назад</Button><Button type="submit" :disabled="busy || Boolean(scheduleError) || nextRuns.length !== 5"><Loader2 v-if="busy" data-icon="inline-start" class="animate-spin" />{{ editMode ? 'Сохранить настройки' : 'Создать и запустить' }}</Button></div>
  </form>
</template>
