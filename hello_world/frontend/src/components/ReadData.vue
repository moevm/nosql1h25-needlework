<script setup lang="ts">
import axios from "axios";
import {ref} from "vue";

let dataInput = "";
let receivedData = ref({});

function readData() {
  axios.get('http://localhost:8000/test/' + dataInput)
      .then((response) => {
        receivedData.value = response.data;
        console.log(response)
      })
      .catch((error: Error) => {
        console.log(error)
      })
}
</script>

<template>
  <div>
    <h1>Введите id для чтения из БД</h1>
    <input type="text" v-model="dataInput" placeholder="id">
    <br>
    <button @click="readData()">ReadData</button>
    <p v-if="Object.keys(receivedData).length">{{receivedData}}</p>
  </div>
</template>

<style scoped>

</style>