<script setup>
import { ref } from "vue";

const query = ref("");
const type = ref("entity");
const emit = defineEmits(["search"]);

function trigger() {
  emit("search", { q: query.value.trim(), type: type.value });
}
</script>

<template>
  <section class="panel row">
    <input
      v-model="query"
      type="text"
      placeholder="Search entities or relations..."
      @keyup.enter="trigger"
    />
    <select v-model="type">
      <option value="entity">Entity</option>
      <option value="relation">Relation</option>
    </select>
    <button @click="trigger">Search</button>
  </section>
</template>
