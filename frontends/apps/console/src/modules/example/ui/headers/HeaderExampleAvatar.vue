<script setup lang="ts">
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import avatarUrl from "../../assets/header-avatar.png";
</script>

<template>
  <Avatar class="size-12">
    <AvatarImage :src="avatarUrl" alt="John Doe" />
    <AvatarFallback>JD</AvatarFallback>
  </Avatar>
</template>
