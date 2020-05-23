import Vue from 'vue';
import axios from 'axios';

// Main data structure.
var data = {
    limit_upcoming: 5,
    limit_processed: 15,
    name: null,
    capture: false,
    uploading: false,
    upcoming: null,
    processed: null,
    previews: null,
    upcoming_events: [],
    recorded_events: [],
};

// create_event creates entries for the event list.
var create_event = function (event, status) {
    return {
        'start': new Date(event.attributes.start).toLocaleString(),
        'end': new Date(event.attributes.end).toLocaleString(),
        'status': status,
    };
}

// update_data gets information from the backend and updates the main data structure 'data'.
var update_data = function () {
    // Get capture agent name.
    axios
        .get('/api/name')
        .then(response => data.name = response.data.name);
    // Get services.
    axios
        .get('/api/services')
        .then(response => {
            data.capture = response.data.meta.services.capture === "busy";
            data.uploading = response.data.meta.services.ingest === "busy";
        });
    // Get events.
    axios
        .get('/api/events')
        .then(response => {
            data.upcoming = response.data.upcoming.length;
            data.processed = response.data.recorded.length;
            data.upcoming_events = response.data.upcoming.map(x => create_event(x, 'upcoming'));
            data.recorded_events = response.data.recorded.map(x => create_event(x, x.attributes.status));
        });
    // Get preview images.
    axios
        .get('/api/previews')
        .then(response => {
            data.previews = response.data.data.map(x => "/img/" + x.id + "?" + Date.now());
        });
};

// Trigger the first update of the main data structure on load.
update_data();

window.onload = function () {
    // Vue App
    var vue = new Vue({
        el: "#app",
        data: data,
        components: {
            'component-preview': {
                props: ['image'],
                template: '<img :src="image" />',
            },
            'component-events': {
                props: ['event'],
                template: `
                <tr>
                    <td>{{ event.start }}</td>
                    <td>{{ event.end }}</td>
                    <td>{{ event.status }}</td>
                </tr>`,
            },
        },
    });
    // Trigger next refresh after set time if over.
    const refresh = new URLSearchParams(window.location.search).get('refresh');
    if (refresh) {
        setInterval(function () {
            update_data();
        }.bind(this), refresh * 1000);
    }
};
