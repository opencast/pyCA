<template>
    <tbody>
    <th colspan="2">{{ metric.header }}</th>
        <template v-for="item in metric.metrics">
            <tr>
                <td>{{ item.name }}</td>
                <td>{{ item.value }}</td>
            </tr>
        </template>
    </tbody>
</template>

<script>
export default {
    props: ['metric'],
};
</script>

<style scoped>
</style>
