<template>
    <tr>
        <td>{{ event.title }}</td>
        <td>{{ event.start }}</td>
        <td>{{ event.end }}</td>
        <td>
            <div class=event_status>
                {{ event.status }}
                <span class=warning v-if="is_error_state(event)">
                <font-awesome-icon icon="exclamation-triangle" />
                </span>
                <span class=action
                      v-if="event.status == 'failed uploading' || event.status == 'paused after recording'"
                      v-on:click="retry_ingest(event)"
                      title="Retry upload">
                    <font-awesome-icon icon="sync" v-bind:class="{ 'fa-spin': event.processing }" />
                </span>
            </div>
        </td>
    </tr>
</template>

<script>
export default {
    props: ['event'],
    methods: {
        is_error_state: event => [
            'partial recording',
            'failed recording'
        ].indexOf(event.status) >= 0,
        retry_ingest: function(event) {
            if (!event.processing) {
                event.processing = true;
                event.status = 'action pending'
                var requestOptions = {
                    method: "PATCH",
                    headers: { "Content-Type": "application/vnd.api+json" },
                    body: JSON.stringify(
                        {"data": [{
                            "attributes": {"status": "finished recording"},
                            "id": event.id,
                            "type": "event"
                        }]})
                };

                fetch("/api/events/" + event.id, requestOptions)
                    .then( function(response) {
                        if (response.status != 200) {throw "Error: request failed - status "; }
                    })
                    .catch(function(error) { console.log(error); })
                    .finally ( () => {
                        event.processing = false;
                    })
            }
        }
    }
};
</script>

<style scoped>
    div.event_status {
        display: flex;
        justify-content: space-between;
    }

    div.event_status span.warning {
        color: red;
    }

    div.event_status span.action {
        cursor: pointer;
    }
</style>
