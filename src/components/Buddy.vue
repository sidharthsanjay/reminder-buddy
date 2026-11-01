<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import {
  answerDone,
  answerLater,
  getConfig,
  gifUrl,
  greetingFor,
  listCharacters,
  type CharacterMeta,
  type Config,
  type Mood,
} from "../api";

const config = ref<Config | null>(null);
const meta = ref<CharacterMeta | undefined>(undefined);
const mood = ref<Mood>("wave");
const message = ref("");
const showButtons = ref(false);
const visible = ref(false);
const src = ref("");

const happyLines = [
  "Nice! 🙌 Hydration hero.",
  "Cheers! 🥂 Back to it.",
  "Good job! 💪 See you later.",
  "Ahh, refreshing. ✨",
];

let unlisten: UnlistenFn | null = null;
let timer: number | undefined;

function setMood(m: Mood) {
  mood.value = m;
  // Cache-bust so the GIF restarts from frame 1 each time.
  src.value = gifUrl(meta.value, m, true);
}

async function refresh() {
  config.value = await getConfig();
  const all = await listCharacters();
  meta.value = all.find((c) => c.id === config.value!.character) ?? all[0];
}

async function onRemind() {
  await refresh();
  visible.value = false;
  message.value = greetingFor(meta.value, config.value?.name ?? "");
  showButtons.value = true;
  setMood("wave");
  requestAnimationFrame(() => (visible.value = true));
}

function yes() {
  showButtons.value = false;
  message.value = happyLines[Math.floor(Math.random() * happyLines.length)];
  setMood("happy");
  window.clearTimeout(timer);
  timer = window.setTimeout(async () => {
    visible.value = false;
    await answerDone();
  }, 2400);
}

function later() {
  showButtons.value = false;
  const mins = config.value?.snooze_min ?? 10;
  message.value = `No worries — I'll check back in ${mins} min. ⏳`;
  setMood("sad");
  window.clearTimeout(timer);
  timer = window.setTimeout(async () => {
    visible.value = false;
    await answerLater();
  }, 2400);
}

onMounted(async () => {
  unlisten = await listen("remind", onRemind);
  // If the window was shown before the listener attached (e.g. first paint), still greet.
  await onRemind();
});

onUnmounted(() => {
  unlisten?.();
  window.clearTimeout(timer);
});
</script>

<template>
  <div class="buddy" :class="{ visible }" data-tauri-drag-region>
    <transition name="pop">
      <div v-if="message" class="bubble" data-tauri-drag-region>
        <p data-tauri-drag-region>{{ message }}</p>
        <div v-if="showButtons" class="actions">
          <button class="yes" @click="yes">Yes, sip! 💧</button>
          <button class="later" @click="later">Later</button>
        </div>
      </div>
    </transition>
    <img class="sprite" :src="src" :alt="meta?.name ?? 'buddy'" draggable="false" data-tauri-drag-region />
  </div>
</template>

<style scoped>
.buddy {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: flex-end;
  padding: 10px;
  gap: 8px;
  opacity: 0;
  transform: translateY(24px);
  transition: opacity 0.35s ease, transform 0.45s cubic-bezier(0.2, 0.9, 0.3, 1.2);
  user-select: none;
  cursor: grab;
}
.buddy.visible {
  opacity: 1;
  transform: translateY(0);
}
.sprite {
  width: 150px;
  height: 150px;
  object-fit: contain;
  image-rendering: auto;
  filter: drop-shadow(0 6px 10px rgba(0, 0, 0, 0.25));
}
.bubble {
  position: relative;
  max-width: 250px;
  background: #ffffff;
  color: #1d2433;
  border-radius: 16px;
  padding: 12px 14px;
  box-shadow: 0 10px 30px rgba(20, 30, 60, 0.22), 0 0 0 1px rgba(20, 30, 60, 0.06);
  font-size: 14px;
  line-height: 1.35;
}
.bubble::after {
  content: "";
  position: absolute;
  right: 48px;
  bottom: -8px;
  width: 16px;
  height: 16px;
  background: #fff;
  transform: rotate(45deg);
  border-radius: 3px;
  box-shadow: 4px 4px 8px rgba(20, 30, 60, 0.08);
}
.bubble p {
  margin: 0 0 8px;
  font-weight: 600;
}
.actions {
  display: flex;
  gap: 8px;
}
button {
  flex: 1;
  border: 0;
  border-radius: 10px;
  padding: 8px 10px;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.08s ease, filter 0.15s ease;
}
button:hover {
  filter: brightness(1.06);
}
button:active {
  transform: scale(0.96);
}
.yes {
  background: linear-gradient(135deg, #3ea7ff, #2f7cf6);
  color: #fff;
}
.later {
  background: #eef2f7;
  color: #3b4453;
}
.pop-enter-from {
  opacity: 0;
  transform: scale(0.85) translateY(6px);
}
.pop-enter-active {
  transition: all 0.25s cubic-bezier(0.2, 0.9, 0.3, 1.3);
}
</style>
