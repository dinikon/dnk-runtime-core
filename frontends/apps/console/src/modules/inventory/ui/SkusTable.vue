<script setup lang="ts">
import {
  Table,
  TableHeader,
  TableHead,
  TableRow,
  TableBody,
  TableCell,
} from "@/components/ui/table";
import type { SkuDto } from "../api/contracts";
defineProps<{ items: SkuDto[] }>();
</script>
<template>
  <Table
    ><TableHeader
      ><TableRow
        ><TableHead>Код</TableHead><TableHead>Название</TableHead
        ><TableHead>Создан</TableHead></TableRow
      ></TableHeader
    ><TableBody
      ><TableRow v-for="item in items" :key="item.id"
        ><TableCell
          ><RouterLink
            :to="{ name: 'inventory-sku', params: { skuId: item.id } }"
            class="font-medium underline underline-offset-4"
            >{{ item.code }}</RouterLink
          ></TableCell
        ><TableCell class="max-w-80 whitespace-normal break-words">{{
          item.title
        }}</TableCell
        ><TableCell>{{
          new Date(item.created_at).toLocaleString("ru-RU")
        }}</TableCell></TableRow
      ></TableBody
    ></Table
  >
</template>
