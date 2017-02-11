#!/bin/bash

set -eux

TMP="$(mktemp)"
NOW="$(date --utc +%Y-%m-%dT%H:%MZ)"
START="$(date -d "1 min" --utc +%Y-%m-%dT%H:%MZ)"
END="$(date -d "2 min" --utc +%Y-%m-%dT%H:%MZ)"

echo '<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<dublincore xmlns="http://www.opencastproject.org/xsd/1.0/dublincore/"
    xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dcterms:creator>demo</dcterms:creator>
  <dcterms:contributor>demo</dcterms:contributor>
  <dcterms:created xsi:type="dcterms:W3CDTF">'"${NOW}"'</dcterms:created>
  <dcterms:temporal xsi:type="dcterms:Period">start='"${START}"'; end='"${END}"'; scheme=W3C-DTF;</dcterms:temporal>
  <dcterms:description>demo</dcterms:description>
  <dcterms:subject>demo</dcterms:subject>
  <dcterms:language>demo</dcterms:language>
  <dcterms:spatial>pyca</dcterms:spatial>
  <dcterms:title>Demo event</dcterms:title>
</dublincore>' > "${TMP}"

PROPERTIES="event.location=pyca
org.opencastproject.workflow.definition=fast
"

cat "${TMP}"

curl -f -i --digest -u opencast_system_account:CHANGE_ME \
    -H "X-Requested-Auth: Digest" \
    'https://octestallinone.virtuos.uos.de/recordings/' \
    -F "dublincore=@${TMP}" \
    -F "agentparameters=${PROPERTIES}"

rm "${TMP}"
