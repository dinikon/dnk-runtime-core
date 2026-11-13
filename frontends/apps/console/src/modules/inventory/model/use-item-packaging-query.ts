import {computed,type Ref} from "vue";
import {useQuery,type UseQueryReturnType} from "@tanstack/vue-query";
import {getItemPackaging} from "../api/item-packaging.api";
import {itemPackagingKeys} from "./item-packaging.query-keys";
import {retryItemPackagings} from "./item-packaging.errors";
import type {ItemPackaging,ItemPackagingsListParams,ItemPackagingsPage} from "./item-packaging.types";
import type {InventoryScopeState} from "./use-inventory-scope";
export function useItemPackagingQuery(itemId:Ref<string>,id:Ref<string>,scope:InventoryScopeState):UseQueryReturnType<ItemPackaging,Error>{
 return useQuery({queryKey:computed(()=>itemPackagingKeys.detail(scope.key.value,itemId.value,id.value)),
 queryFn:({queryKey,signal})=>getItemPackaging(queryKey[5],queryKey[7],signal),
 enabled:computed(()=>scope.ready.value&&!!itemId.value&&!!id.value),staleTime:30_000,retry:retryItemPackagings});
}
