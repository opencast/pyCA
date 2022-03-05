<template>
    <div>
        <form v-if='!this.active' id=schedule v-on:submit=schedule>
            <label for=title>Title</label>
            <input id=title type=text placeholder='pyCA Recording' v-model=title required />
            <br />
            <label for=creator>Creator</label>
            <input id=creator type=text placeholder=Administrator v-model=creator required />
            <br />
            <label for=duration>Duration (min)</label>
            <input id=duration type=number placeholder=30 v-model.number=duration required />
            <br />
            <input type=submit value=Start />
        </form>
        <div v-if='this.active' style='color: green;padding: 15px'>
            Event is being scheduled…
        </div>
    </div>
</template>

<script>
export default {
    data() {
        return {
        active: false,
        title: 'pyCA Recording',
        creator: 'Administrator',
        duration: 5,
    }},
    methods: {
        schedule: function(event) {
            event.preventDefault();
            this.active = true;
            let requestOptions = {
                method: 'POST',
                headers: { 'Content-Type': 'application/vnd.api+json' },
                body: JSON.stringify(
                    {'data': [{
                        'title': this.title,
                        'creator': this.creator,
                        'duration': this.duration * 60
                    }]})
            };

            fetch('/api/schedule', requestOptions)
                .then(response => {
                    if (response.status == 409) {
                        alert('Conflict: A scheduled recording exists during this time.');
                        throw 'Error: Scheduling conflict';
                    } else if (response.status != 200) {
                        throw 'Error: request failed';
                    }
                })
                .catch(function(error) {
                    console.log(error);
                })
                .finally(() => {
                    this.active = false;
                })
        }
    }
};
</script>
