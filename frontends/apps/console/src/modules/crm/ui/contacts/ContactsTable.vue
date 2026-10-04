<script setup lang="ts">
import { MoreHorizontal } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Contact } from "../../model/crm.types";
import CrmRecordLink from "../common/CrmRecordLink.vue";
import {
  crmRecordRoute,
  useCrmNavigation,
} from "../../model/use-crm-navigation";
import { useRouter } from "vue-router";

defineProps<{ items: Contact[] }>();
const emit = defineEmits<{ delete: [item: Contact] }>();
const router = useRouter();
const navigation = useCrmNavigation();
function formatDate(value: string) {
  return new Date(value).toLocaleString("uk-UA");
}
function openRow(event: MouseEvent, id: string) {
  if (event.defaultPrevented || (event.target as Element).closest("a, button"))
    return;
  if (event.metaKey || event.ctrlKey) {
    window.open(router.resolve(crmRecordRoute("contacts", id)).href, "_blank");
    return;
  }
  navigation.preview("contacts", id);
}
function onRowKeydown(event: KeyboardEvent, id: string) {
  if (event.target !== event.currentTarget) return;
  if (event.key !== "Enter" && event.key !== " ") return;
  event.preventDefault();
  navigation.preview("contacts", id);
}
</script>

<template>
  <div class="w-full min-w-0 overflow-x-auto rounded-lg border bg-background">
    <Table>
      <TableHeader
        ><TableRow>
          <TableHead>ФИО</TableHead><TableHead>Создан</TableHead>
          <TableHead>Обновлён</TableHead
          ><TableHead><span class="sr-only">Действия</span></TableHead>
        </TableRow></TableHeader
      >
      <TableBody>
        <TableRow
          v-for="item in items"
          :key="item.id"
          class="cursor-pointer"
          tabindex="0"
          @click="openRow($event, item.id)"
          @keydown="onRowKeydown($event, item.id)"
        >
          <TableCell class="font-medium">
            <CrmRecordLink
              kind="contacts"
              :id="item.id"
              class="text-primary hover:underline"
            >
              {{ item.displayName }}
            </CrmRecordLink>
          </TableCell>
          <TableCell>{{ formatDate(item.createdAt) }}</TableCell>
          <TableCell>{{ formatDate(item.updatedAt) }}</TableCell>
          <TableCell class="text-right">
            <DropdownMenu>
              <DropdownMenuTrigger as-child
                ><Button
                  variant="ghost"
                  size="icon"
                  aria-label="Действия контакта"
                  ><MoreHorizontal /></Button
              ></DropdownMenuTrigger>
              <DropdownMenuContent align="end"
                ><DropdownMenuGroup>
                  <DropdownMenuItem
                    @click="router.push(crmRecordRoute('contacts', item.id))"
                    >Открыть страницу</DropdownMenuItem
                  >
                  <DropdownMenuItem
                    variant="destructive"
                    @click="emit('delete', item)"
                    >Удалить</DropdownMenuItem
                  >
                </DropdownMenuGroup></DropdownMenuContent
              >
            </DropdownMenu>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  </div>
</template>
