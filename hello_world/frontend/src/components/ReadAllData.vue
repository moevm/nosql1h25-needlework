<script setup lang="ts">
import axios from "axios";
import {ref} from "vue";

let receivedData = ref({});

function readData() {
  axios.get('http://localhost:8000/test/')
      .then((response) => {
        receivedData.value = response.data;
      })
      .catch((error: Error) => {
        console.log(error)
      })
}
</script>

<template>
  <div>
    <h1>Получить все данные из БД (в тестовых целях)</h1>
    <button @click="readData()">ReadData</button>
    <p v-if="Object.keys(receivedData).length">{{receivedData}}</p>
  </div>
</template>

<style scoped>

</style>