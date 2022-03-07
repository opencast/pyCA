import Vue from 'vue';
import axios from 'axios';

import { library } from '@fortawesome/fontawesome-svg-core'
import { faExclamationTriangle } from '@fortawesome/free-solid-svg-icons/faExclamationTriangle'
import { faSync } from '@fortawesome/free-solid-svg-icons/faSync'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'

import Event from './Event.vue'
import Metrics from './Metrics.vue'
import Preview from './Preview.vue'

library.add(faExclamationTriangle)
library.add(faSync)
Vue.component('font-awesome-icon', FontAwesomeIcon)

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
    metrics: [],
    logs: [],
};

// create_event creates entries for the event list.
var create_event = function (event, status, id) {
    return {
        'title': event.attributes.title,
        'start': new Date(event.attributes.start * 1000).toLocaleString(),
        'end': new Date(event.attributes.end * 1000).toLocaleString(),
        'status': status,
        'id': id
    };
}

// format_bytes format a number of bytes in a representable format inclusive unit.
function format_bytes(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const dm = 2;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

// update_data gets information from the backend and updates the main data structure 'data'.
var update_data = function () {
    // Get capture agent name.
    axios
        .get('/api/name')
        .then(response => data.name = response.data.meta.name);
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
            data.recorded_events = response.data.data
                .filter(x => x.attributes.status !== "upcoming")
                .map(x => create_event(x, x.attributes.status, x.id));
            data.processed = data.recorded_events.length;
            var event_in_processing = data.processed > 0 ? data.recorded_events[0].id : null;
            data.upcoming_events = response.data.data
                .filter(x => x.attributes.status === "upcoming")
                .filter(x => x.id !== event_in_processing)
                .map(x => create_event(x, x.attributes.status, x.id));
            data.upcoming = data.upcoming_events.length;
        });
    // Get preview images.
    axios
        .get('/api/previews')
        .then(response => {
            data.previews = response.data.data.map(x => "/img/" + x.attributes.id + "?" + Date.now());
        });

    // Get metrics.
    axios
        .get('/api/metrics')
        .then(response => {
            data.metrics = [];

            // Machine related metrics
            var machine = {
                'header': 'Machine',
                'metrics': [],
            };
            // Get load
            var load = response.data.meta.load;
            if (load) {
                machine.metrics.push({
                    'name': 'Load Averages',
                    'value': `${load["1m"]} ${load["5m"]} ${load["15m"]}`,
                });
            }
            // Get disk usage
            var disk_usage = response.data.meta.disk_usage_in_bytes;
            if (disk_usage) {
                const used = (disk_usage.used / disk_usage.total) * 100;
                machine.metrics.push({
                    'name': 'Disk Usage',
                    'value': `${used.toFixed(0)}% (${format_bytes(disk_usage.free)} free)`,
                });
            }
            // Get memory usage
            var memory_usage = response.data.meta.memory_usage_in_bytes;
            if (memory_usage) {
                const used = (memory_usage.used / memory_usage.total) * 100;
                machine.metrics.push({
                    'name': 'Memory Usage',
                    'value': `${used.toFixed(0)}% (${format_bytes(memory_usage.free)} free, `
                        + `${format_bytes(memory_usage.buffers + memory_usage.cached)} buffers/cached)`,
                });
            }
            // Add machine metrics
            if (machine.metrics && machine.metrics.length) {
                data.metrics.push(machine)
            }

            // Service related metrics
            const services = {
                'header': 'Services',
                'metrics': response.data.meta.services.map(
                    service => ({
                        'name': service.name[0].toUpperCase() + service.name.slice(1),
                        'value': service.status,
                    }))
            };
            // Add Service metrics
            if (services.metrics && services.metrics.length) {
                data.metrics.push(services)
            }

            // Upstream related metrics
            const upstream = {
                'header': 'Upstream',
                'metrics': [{
                    'name': 'Last Schedule Update',
                    'value': response.data.meta.upstream.last_synchronized ?
                        Date(response.data.meta.upstream.last_synchronized).toString() :
                        'never'
                }]
            };
            // Add upstream metrics
            if (upstream.metrics && upstream.metrics.length) {
                data.metrics.push(upstream)
            }
        });

    axios
        .get('/api/logs')
        .then(response => {
            data.logs = response.data.data[0].attributes.lines;
        })
        .catch(error => {
            if (error.response.status != 404) {
                console.error(error);
            }
        });
};

window.onload = function () {
    // Vue App
    new Vue({
        el: "#app",
        data: data,
        components: {
            Preview,
            Event,
            Metrics,
        },
        created: update_data,
    });
    // Trigger next refresh after set time if over.
    const refresh = new URLSearchParams(window.location.search).get('refresh') || 10;
    if (refresh) {
        setInterval(function () {
            update_data();
        }.bind(this), refresh * 1000);
    }
};
