<script setup lang="ts">
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { CatalogItem, CatalogAttribute } from "../../model/catalog.types";
import type { ProductSection } from "../../model/product.types";
import { sectionTitles } from "../../model/product-presentation";
import CatalogItemFieldsForm from "../forms/CatalogItemFieldsForm.vue";
defineProps<{
  item: CatalogItem;
  section: ProductSection;
  locale: string;
  pending: boolean;
  reset: number;
  attributes: CatalogAttribute[];
  schemaVersion: number;
  dirty?: boolean;
  validationError?: string;
}>();
defineEmits<{
  save: [value: Record<string, unknown>];
  dirty: [value: boolean];
}>();
</script>
<template>
  <Card class="min-w-0 shadow-none" :data-section="section"
    ><CardHeader
      ><CardTitle class="flex flex-wrap items-center gap-2"
        >{{ sectionTitles[section]
        }}<Badge v-if="dirty" variant="outline"
          >Есть изменения</Badge
        ></CardTitle
      ></CardHeader
    ><CardContent
      ><CatalogItemFieldsForm
        :validation-error="validationError"
        :item="item"
        :section="section"
        :locale="locale"
        :pending="pending"
        :reset="reset"
        :attributes="attributes"
        :schema-version="schemaVersion"
        @dirty="$emit('dirty', $event)"
        @save="$emit('save', $event)" /></CardContent
  ></Card>
</template>
