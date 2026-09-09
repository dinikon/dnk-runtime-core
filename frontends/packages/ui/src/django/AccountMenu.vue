<script setup lang="ts">
import { Menu } from "@lucide/vue";
import { Button } from "@dnk/ui/components/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetTrigger } from "@dnk/ui/components/sheet";
defineProps<{ links: { href: string; text: string; current: boolean }[] }>();
</script>
<template>
  <Sheet>
    <SheetTrigger as-child><Button variant="outline" class="w-full justify-between"><span>Аккаунт и безопасность</span><Menu /></Button></SheetTrigger>
    <SheetContent side="left">
      <SheetHeader class="pr-14"><SheetTitle>Аккаунт и безопасность</SheetTitle><SheetDescription>Профиль, способы входа и ваши устройства</SheetDescription></SheetHeader>
      <nav class="flex flex-col gap-1 px-4" aria-label="Настройки аккаунта">
        <Button v-for="link in links" :key="link.href" as="a" :href="link.href" :variant="link.current ? 'secondary' : 'ghost'" :aria-current="link.current ? 'page' : undefined" class="justify-start">{{ link.text }}</Button>
      </nav>
    </SheetContent>
  </Sheet>
</template>
