<script setup lang="ts">
import Buddy from "./components/Buddy.vue";
import Settings from "./components/Settings.vue";

// Both windows load the same bundle; the query string picks the view.
const view = new URLSearchParams(window.location.search).get("view") ?? "settings";
document.documentElement.dataset.view = view;
</script>

<template>
  <Buddy v-if="view === 'buddy'" />
  <Settings v-else />
</template>
