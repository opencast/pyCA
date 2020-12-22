<template>
    <img :src="image" />
</template>

<script>
export default {
    props: ['image'],
};
</script>

<style scoped>
  img {
    max-width: 90%;
    max-height: 300px;
  }
</style>
