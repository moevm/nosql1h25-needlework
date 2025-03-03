<script setup lang="ts">
import axios from "axios";
import {ref} from "vue";

let dataInput = "";
let receivedData = ref({});

function sendData() {
  axios.post('http://localhost:8000/test', {
    "test": dataInput
  })
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
    <h1>Введите данные для ввода в БД</h1>
    <input type="text" v-model="dataInput" placeholder="input data">
    <br>
    <button @click="sendData()">SendData</button>
    <p v-if="Object.keys(receivedData).length">{{receivedData}}</p>
  </div>
</template>

<style scoped>

</style>