<script setup lang="ts">
import { computed } from "vue";
import { useFunnelsPageState } from "../model/use-funnels-page-state";
import { useRouter } from "vue-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Empty,
  EmptyHeader,
  EmptyTitle,
  EmptyDescription,
} from "@/components/ui/empty";
import { getApiErrorMessage } from "@/app/providers/http";
import { useFunnels } from "../model/funnel.queries";
const router = useRouter();
const { search, modelKey, offset, page, setType } = useFunnelsPageState();
const querySearch = computed(() =>
  String(router.currentRoute.value.query.q ?? ""),
);
const funnels = useFunnels(modelKey, querySearch, offset);
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-auto pb-6">
    <header class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p class="text-sm text-muted-foreground">CRM</p>
        <h1 class="text-2xl font-semibold">Воронки</h1>
        <p class="text-sm text-muted-foreground">
          Процессы и стадии для лидов и сделок.
        </p>
      </div>
      <Button
        @click="
          router.push({
            path: '/funnels/new',
            query: { type: modelKey || undefined },
          })
        "
        >Новая воронка</Button
      >
    </header>
    <div class="flex flex-wrap gap-3">
      <NativeSelect
        aria-label="Тип воронок"
        :model-value="modelKey"
        @update:model-value="setType(String($event))"
        ><option value="">Все типы</option>
        <option value="crm.lead">Лиды</option>
        <option value="crm.deal">Сделки</option></NativeSelect
      ><Input
        v-model="search"
        class="max-w-sm"
        aria-label="Поиск воронок"
        placeholder="Название воронки"
      />
    </div>
    <Skeleton v-if="funnels.isPending.value" class="h-40 w-full" /><Alert
      v-else-if="funnels.error.value"
      variant="destructive"
      ><AlertDescription
        >{{
          getApiErrorMessage(
            funnels.error.value,
            "Не удалось выполнить действие.",
          )
        }}<Button variant="outline" @click="funnels.refetch()"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    ><Empty v-else-if="!funnels.data.value?.items.length"
      ><EmptyHeader
        ><EmptyTitle>Воронки не найдены</EmptyTitle
        ><EmptyDescription
          >Измените фильтры или создайте новый процесс.</EmptyDescription
        ></EmptyHeader
      ></Empty
    >
    <div v-else class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <Card v-for="f in funnels.data.value?.items" :key="f.id"
        ><CardHeader
          ><CardTitle>{{ f.name }}</CardTitle
          ><CardDescription
            >{{ f.modelKey === "crm.lead" ? "Лиды" : "Сделки" }} ·
            {{ f.stages.length }} стадий</CardDescription
          ></CardHeader
        ><CardContent
          ><Badge v-if="f.isDefault" variant="secondary">По умолчанию</Badge>
          <p class="mt-2 text-sm text-muted-foreground">
            {{ f.stages.map((s) => s.name).join(" → ") }}
          </p></CardContent
        ><CardFooter class="flex flex-wrap gap-2"
          ><Button variant="outline" @click="router.push('/funnels/' + f.id)"
            >Настроить</Button
          ><Button
            variant="ghost"
            @click="
              router.push({
                path: f.modelKey === 'crm.lead' ? '/crm/leads' : '/crm/deals',
                query: { funnel: f.id },
              })
            "
            >Открыть канбан</Button
          ></CardFooter
        ></Card
      >
    </div>
    <div v-if="(funnels.data.value?.total ?? 0) > 100" class="flex gap-3">
      <Button variant="outline" :disabled="!offset" @click="page(offset / 100)"
        >Назад</Button
      ><Button
        variant="outline"
        :disabled="offset + 100 >= (funnels.data.value?.total ?? 0)"
        @click="page(offset / 100 + 2)"
        >Далее</Button
      >
    </div>
  </div>
</template>
