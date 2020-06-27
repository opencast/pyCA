pyCA API Documentation
======================

The pyCA web interface comes with a JSON API to programmatically modify and
retrieve information about the capture agent. Note that this API is only
available if the UI is configured and started which is not the case by
default.

.. contents::


GET /api/name
-------------

A JSON representation of name of the pyCA instance.

cURL example::

  % curl -u admin:opencast \
      -H 'content-type: application/vnd.api+json' \
      'http://127.0.0.1:5000/api/name'
  {
    "meta": {
      "name": "pyca"
    }
  }


GET /api/previews
-----------------

A JSON representation of the current available previews.

cURL example::

  % curl -u admin:opencast \
      -H 'content-type: application/vnd.api+json' \
      'http://127.0.0.1:5000/api/previews'
  {
    "data": [
      {
        "attributes": {
          "id": 1
        },
        "id": "1",
        "type": "preview"
      }
    ]
  }


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


GET /api/metrics
-----------------

Metrics about the services of pyCA and the machine it is running on.

cURL example::

  % curl -u admin:opencast \
      -H 'content-type: application/vnd.api+json' \
      'http://127.0.0.1:5000/api/metrics'
  {
    "meta": {
      "disk_usage_in_bytes": {
        "free": 23310340096,
        "total": 117042683904,
        "used": 87742750720
      },
      "load": {
        "15m": 0.21,
        "1m": 0.38,
        "5m": 0.27
      },
      "memory_usage_in_bytes": {
        "available": 29922299904,
        "buffers": 155013120,
        "cached": 1310781440,
        "free": 28908437504,
        "total": 33695797248,
        "used": 3321565184
      },
      "services": [
        {
          "name": "agentstate",
          "status": "busy"
        },
        {
          "name": "capture",
          "status": "idle"
        },
        {
          "name": "ingest",
          "status": "idle"
        },
        {
          "name": "schedule",
          "status": "busy"
        }
      ]
    }
  }


GET /api/logs
-------------

Get logs of pyCA gather via the command specified in the configuration.
By default, this API endpoint is disabled and will return a HTTP 404 status
code.

cURL example::

  %curl -u admin:opencast \
      -H 'content-type: application/vnd.api+json' \
      'http://127.0.0.1:5000/api/logs?limit=2'
  {
    "data": [
      {
        "attributes": {
          "lines": [
            "-- Logs begin at Fri 2020-04-24 23:25:38 CEST, end at Wed 2020-07-01 21:34:56 CEST. --",
            "Jun 23 02:44:55 example.io systemd[1]: pyca.service: Succeeded.",
            "Jun 23 02:44:55 example.io systemd[1]: Stopped PyCA."
          ]
        },
        "id": "1593632272",
        "type": "logs"
      }
    ]
  }
