<script setup lang="ts">
import { returnDirectionLabel } from "../../model/return-origin.types";
import { returnStatusLabels } from "../../model/return-page-state";
import type { ReturnDocument } from "../../model/return.types";
defineProps<{ document: ReturnDocument }>();
</script>
<template>
  <div class="flex w-full max-w-5xl shrink-0 flex-col gap-5">
    <section class="rounded-lg border bg-card p-4">
      <h2 class="mb-3 text-lg font-semibold">Реквизиты возврата</h2>
      <p class="mb-4 whitespace-pre-wrap break-words text-sm">
        <strong>Причина возврата:</strong> {{ document.reason }}<br /><strong
          >Направление:</strong
        >
        {{ returnDirectionLabel(document.direction) }}
      </p>
      <dl class="grid min-w-0 gap-4 text-sm sm:grid-cols-2">
        <div>
          <dt class="text-muted-foreground">Статус</dt>
          <dd>{{ returnStatusLabels[document.status] }}</dd>
        </div>
        <div>
          <dt class="text-muted-foreground">Операция</dt>
          <dd>Возврат</dd>
        </div>
        <div>
          <dt class="text-muted-foreground">Склад</dt>
          <dd>{{ document.warehouseCode }} — {{ document.warehouseName }}</dd>
        </div>
        <div>
          <dt class="text-muted-foreground">Компания-владелец</dt>
          <dd>{{ document.ownerName ?? "Компания недоступна" }}</dd>
        </div>
        <div>
          <dt class="text-muted-foreground">Создано</dt>
          <dd>
            <time :datetime="document.createdAt">{{
              new Date(document.createdAt).toLocaleString()
            }}</time>
          </dd>
        </div>
        <div>
          <dt class="text-muted-foreground">Версия документа</dt>
          <dd>{{ document.version }}</dd>
        </div>
      </dl>
      <p
        v-if="document.status === 'DRAFT'"
        class="mt-4 rounded-md bg-muted p-3 text-sm"
      >
        Черновик возврата. Физические остатки ещё не изменены.
      </p>
    </section>
    <section class="min-w-0 rounded-lg border bg-card p-4">
      <h2 class="mb-3 text-lg font-semibold">Плановые строки</h2>
      <p
        v-if="!document.lines.length"
        class="py-4 text-sm text-muted-foreground"
      >
        Плановых строк пока нет. Сохранён пустой черновик.
      </p>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead>
            <tr>
              <th class="p-2">№</th>
              <th class="p-2">SKU</th>
              <th class="p-2">Введено</th>
              <th class="p-2">Коэффициент</th>
              <th class="p-2">План в базовой единице</th>
              <th class="p-2">Выполнено</th>
              <th class="p-2">Осталось</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="line in document.lines" :key="line.id" class="border-t">
              <td class="p-2">{{ line.position + 1 }}</td>
              <td class="whitespace-nowrap p-2 font-mono">{{ line.sku }}</td>
              <td class="whitespace-nowrap p-2">
                {{ line.sourceQuantity }} {{ line.sourceUom }}
              </td>
              <td class="p-2">{{ line.factorToBase }}</td>
              <td class="whitespace-nowrap p-2">
                {{ line.plannedQty }} {{ line.baseUom }}
              </td>
              <td class="whitespace-nowrap p-2">
                {{ line.executedQty }} {{ line.baseUom }}
              </td>
              <td class="whitespace-nowrap p-2">
                {{ line.remainingQty }} {{ line.baseUom }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="mt-3 text-xs text-muted-foreground">
        Коды SKU, единицы и коэффициенты сохранены в документе. Изменения
        справочников не пересчитывают этот план.
      </p>
    </section>
  </div>
</template>
