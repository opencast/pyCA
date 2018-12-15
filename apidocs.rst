pyCA API Documentation
======================

The pyCA web interface comes with a JSON API to programmatically modify and
retrieve information about the capture agent. Note that this API is only
available if the UI is configured and started which is not the case by
default.

.. contents::


GET /api/services
-----------------

A JSON representation of pyCA's internal service states.

cURL example::

  % curl -u admin:opencast \
      -H 'content-type: application/vnd.api+json' \
      'http://127.0.0.1:5000/api/services'
  {
    "meta": {
      "services": {
        "agentstate": "stopped",
        "capture": "stopped",
        "ingest": "stopped",
        "schedule": "stopped"
      }
    }
  }


GET /api/events/
----------------

List all events recorded or cached by pyCA.

cURL example::

  {
    "data": [
      {
        "attributes": {
          "data": {
            "attach": [
              ...
            ],
            "description": "demo",
            "dtend": 1544906940,
            "dtstamp": 1544906826,
            "dtstart": 1544906820,
            "last-modified": "20181215T204631Z",
            "location": "pyca",
            "organizer;cn=demo": "mailto:demo@opencast.tld",
            "summary": "Demo event",
            "uid": "ce076210-0a54-4a45-ba67-1c25a5740025"
          },
          "end": 1544906940,
          "start": 1544906820,
          "status": "finished uploading",
          "title": "Demo event",
          "uid": "ce076210-0a54-4a45-ba67-1c25a5740025"
        },
        "id": "ce076210-0a54-4a45-ba67-1c25a5740025",
        "type": "event"
      },
      ...
    ]
  }


GET /api/events/<uid>
---------------------

List all data for a single event recorded or cached by pyCA.

cURL example::

  % curl -u admin:opencast \
      -H 'content-type: application/vnd.api+json' \
      'http://127.0.0.1:5000/api/events/ce076210-0a54-4a45-ba67-1c25a5740025'
  {
    "data": [
      {
        "attributes": {
          "data": {
            "attach": [
              ...
            ],
            "description": "demo",
            "dtend": 1544906940,
            "dtstamp": 1544906826,
            "dtstart": 1544906820,
            "last-modified": "20181215T204631Z",
            "location": "pyca",
            "organizer;cn=demo": "mailto:demo@opencast.tld",
            "summary": "Demo event",
            "uid": "ce076210-0a54-4a45-ba67-1c25a5740025"
          },
          "end": 1544906940,
          "start": 1544906820,
          "status": "finished uploading",
          "title": "Demo event",
          "uid": "ce076210-0a54-4a45-ba67-1c25a5740025"
        },
        "id": "ce076210-0a54-4a45-ba67-1c25a5740025",
        "type": "event"
      }
    ]
  }


DELETE /api/events/<uid>
------------------------

Delete a single event recorded by pyCA.
Use the `?hard=true` parameter to delete the recorded files on disk as well.

- Returns 204 if the action was successful.
- Returns 404 if event does not exist

cURL example::

  % curl -u admin:opencast -X DELETE \
      -H 'content-type: application/vnd.api+json' \
      'http://127.0.0.1:5000/api/events/ce076210-0a54-4a45-ba67-1c25a5740025'


PATCH /api/events/<uid>
-----------------------

Modify an event specified by its uid. The modifications for the event
are expected as JSON with the content type correctly set in the request.

The request *must* contain:

- `.data[0].id = <uid>`
- `.data[0].type = "event"`

The request *may* contain:

- `.data[0].attributes.start`
- `.data[0].attributes.end`
- `.data[0].attributes.status`

Note that this method works for recorded events only. Upcoming events part
of the scheduler cache cannot be modified.

cURL example::

  % curl -u admin:opencast -X PATCH \
      -H 'content-type: application/vnd.api+json' \
      --data '{"data":[{
                "attributes":{
                  "start": 123,
                  "end": 234,
                  "status": "finished uploading"
                },
                "id": "24904788-daf4-42a3-961e-01927c8e8041",
                "type": "event"}]}' \
      'http://127.0.0.1:5000/api/events/24904788-daf4-42a3-961e-01927c8e8041'
  {
    "data": [
      {
        "attributes": {
          "data": {
            "attach": [
              ...
            ],
            "description": "demo",
            "dtend": 1544905380,
            "dtstamp": 1544905266,
            "dtstart": 1544905260,
            "last-modified": "20181215T202056Z",
            "location": "pyca",
            "organizer;cn=demo": "mailto:demo@opencast.tld",
            "summary": "Demo event",
            "uid": "24904788-daf4-42a3-961e-01927c8e8041"
          },
          "end": 234,
          "start": 123,
          "status": "finished uploading",
          "title": "Demo event",
          "uid": "24904788-daf4-42a3-961e-01927c8e8041"
        },
        "id": "24904788-daf4-42a3-961e-01927c8e8041",
        "type": "event"
      }
    ]
  }
