<template>
    <tbody>
        <th colspan="2">{{ metric.header }}</th>
        <tr v-for="item in metric.metrics" :key="item.id">
            <td>{{ item.name }}</td>
            <td>{{ item.value }}</td>
        </tr>
    </tbody>
</template>

<script>
export default {
    props: ['metric'],
};
</script>

<style scoped>
</style>
