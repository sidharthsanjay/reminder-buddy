<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import {
  getConfig,
  getStatus,
  gifUrl,
  listCharacters,
  remindNow,
  saveConfig,
  type CharacterMeta,
  type Config,
  type Corner,
} from "../api";

const config = ref<Config>({
  name: "",
  character: "me",
  interval_min: 45,
  snooze_min: 10,
  autostart: false,
  corner: "bottom-right",
});
const characters = ref<CharacterMeta[]>([]);
const secondsLeft = ref(0);
const waiting = ref(false);
const saved = ref(false);
const busy = ref(false);

const corners: { value: Corner; label: string }[] = [
  { value: "bottom-right", label: "Bottom right" },
  { value: "bottom-left", label: "Bottom left" },
  { value: "top-right", label: "Top right" },
  { value: "top-left", label: "Top left" },
];

const countdown = computed(() => {
  if (waiting.value) return "Buddy is on screen now";
  const s = Math.max(0, secondsLeft.value);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `Next reminder in ${m}:${r.toString().padStart(2, "0")}`;
});

let poll: number | undefined;

async function load() {
  config.value = await getConfig();
  characters.value = await listCharacters();
  if (!characters.value.some((c) => c.id === config.value.character) && characters.value[0]) {
    config.value.character = characters.value[0].id;
  }
}

async function tick() {
  try {
    const s = await getStatus();
    secondsLeft.value = s.seconds_left;
    waiting.value = s.waiting_for_answer;
  } catch {
    /* window may be closing */
  }
}

async function save() {
  busy.value = true;
  try {
    await saveConfig({ ...config.value });
    saved.value = true;
    setTimeout(() => (saved.value = false), 1800);
    await tick();
  } finally {
    busy.value = false;
  }
}

async function test() {
  await saveConfig({ ...config.value });
  await remindNow();
}

onMounted(async () => {
  await load();
  await tick();
  poll = window.setInterval(tick, 1000);
});
onUnmounted(() => window.clearInterval(poll));
</script>

<template>
  <main class="page">
    <header class="hero">
      <div>
        <p class="eyebrow">Reminder Buddy</p>
        <h1>Small reminders. Better you.</h1>
        <p class="sub">{{ countdown }}</p>
      </div>
      <button class="ghost" @click="test">Test reminder now</button>
    </header>

    <section class="card">
      <h2>Your name</h2>
      <input v-model="config.name" type="text" placeholder="e.g. Sam (optional)" maxlength="30" />
      <p class="hint">Used in the greeting. Leave blank for a friendly default.</p>
    </section>

    <section class="card">
      <h2>Pick your buddy</h2>
      <div class="grid">
        <button
          v-for="c in characters"
          :key="c.id"
          class="char"
          :class="{ active: c.id === config.character }"
          @click="config.character = c.id"
        >
          <img :src="gifUrl(c, 'idle')" :alt="c.name" />
          <span class="name">{{ c.name }}</span>
          <span v-if="c.tagline" class="tag">{{ c.tagline }}</span>
        </button>
      </div>
      <p class="hint">
        Add your own: drop PNGs into <code>characters/&lt;id&gt;/</code> and run
        <code>python tools/make_character.py</code> (see README).
      </p>
    </section>

    <section class="card two">
      <div>
        <h2>Remind every</h2>
        <div class="range">
          <input v-model.number="config.interval_min" type="range" min="5" max="180" step="5" />
          <strong>{{ config.interval_min }} min</strong>
        </div>
      </div>
      <div>
        <h2>“Later” snoozes for</h2>
        <div class="range">
          <input v-model.number="config.snooze_min" type="range" min="1" max="60" step="1" />
          <strong>{{ config.snooze_min }} min</strong>
        </div>
      </div>
    </section>

    <section class="card two">
      <div>
        <h2>Screen corner</h2>
        <select v-model="config.corner">
          <option v-for="c in corners" :key="c.value" :value="c.value">{{ c.label }}</option>
        </select>
      </div>
      <div>
        <h2>Startup</h2>
        <label class="check">
          <input v-model="config.autostart" type="checkbox" />
          Start with Windows
        </label>
      </div>
    </section>

    <footer class="bar">
      <span class="hint">Closing this window keeps the buddy running in the tray.</span>
      <button class="primary" :disabled="busy" @click="save">
        {{ saved ? "Saved ✓" : "Save" }}
      </button>
    </footer>
  </main>
</template>

<style scoped>
.page {
  max-width: 640px;
  margin: 0 auto;
  padding: 24px 24px 96px;
  display: grid;
  gap: 16px;
}
.hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 8px 0 4px;
}
.eyebrow {
  margin: 0 0 4px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-size: 11px;
  color: #6b7a90;
  font-weight: 700;
}
h1 {
  margin: 0;
  font-size: 24px;
  letter-spacing: -0.01em;
}
.sub {
  margin: 6px 0 0;
  color: #2f7cf6;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.card {
  background: #fff;
  border-radius: 16px;
  padding: 18px;
  box-shadow: 0 1px 2px rgba(20, 30, 60, 0.06), 0 8px 24px rgba(20, 30, 60, 0.06);
}
.card.two {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}
h2 {
  margin: 0 0 10px;
  font-size: 14px;
  color: #3b4453;
}
input[type="text"],
select {
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #d9e0ea;
  font: inherit;
  background: #fbfcfe;
}
input[type="text"]:focus,
select:focus {
  outline: 2px solid #9cc5ff;
  border-color: #2f7cf6;
}
.hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: #6b7a90;
}
code {
  background: #eef2f7;
  padding: 1px 5px;
  border-radius: 5px;
  font-size: 11.5px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 10px;
}
.char {
  display: grid;
  justify-items: center;
  gap: 4px;
  padding: 12px 8px 10px;
  border-radius: 14px;
  border: 2px solid transparent;
  background: #f4f7fb;
  cursor: pointer;
  font: inherit;
  transition: transform 0.12s ease, border-color 0.15s ease, background 0.15s ease;
}
.char:hover {
  transform: translateY(-2px);
}
.char.active {
  border-color: #2f7cf6;
  background: #eaf3ff;
}
.char img {
  width: 84px;
  height: 84px;
  object-fit: contain;
}
.char .name {
  font-weight: 700;
  font-size: 13px;
}
.char .tag {
  font-size: 11px;
  color: #6b7a90;
}
.range {
  display: flex;
  align-items: center;
  gap: 12px;
}
.range input {
  flex: 1;
  accent-color: #2f7cf6;
}
.range strong {
  min-width: 64px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.check {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 0;
  cursor: pointer;
}
.check input {
  width: 18px;
  height: 18px;
  accent-color: #2f7cf6;
}
.bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 24px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(10px);
  border-top: 1px solid #e3e8f0;
}
button.primary,
button.ghost {
  border: 0;
  border-radius: 10px;
  padding: 10px 18px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}
button.primary {
  background: linear-gradient(135deg, #3ea7ff, #2f7cf6);
  color: #fff;
  min-width: 110px;
}
button.primary:disabled {
  opacity: 0.6;
}
button.ghost {
  background: #eef2f7;
  color: #2f7cf6;
  white-space: nowrap;
}
</style>
