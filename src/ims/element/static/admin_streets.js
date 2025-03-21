"use strict";
///<reference path="ims.ts"/>
// See the file COPYRIGHT for copyright information.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Initialize UI
//
async function initAdminStreetsPage() {
    detectTouchDevice();
    const { err } = await loadStreets();
    if (err == null) {
        drawStreets();
    }
}
let streets = {};
async function loadStreets() {
    const { json, err } = await fetchJsonNoThrow(url_streets, null);
    if (err != null) {
        const message = `Failed to load streets: ${err}`;
        console.error(message);
        window.alert(message);
        return { err: message };
    }
    streets = json;
    return { err: null };
}
let _streetsTemplate = null;
let _streetsEntryTemplate = null;
function drawStreets() {
    const container = document.getElementById("event_streets_container");
    if (_streetsTemplate == null) {
        _streetsTemplate = container.querySelectorAll(".event_streets")[0];
        _streetsEntryTemplate = _streetsTemplate.querySelector("ul").querySelector("li");
    }
    container.replaceChildren();
    for (const event of events) {
        const eventStreets = _streetsTemplate.cloneNode(true);
        // Add an id to the element for future reference
        eventStreets.id = `event_streets_${event}`;
        // Add to container
        container.append(eventStreets);
        updateEventStreets(event);
    }
}
function updateEventStreets(event) {
    const eventStreets = streets[event];
    if (eventStreets == null) {
        return;
    }
    const eventStreetsElement = document.getElementById("event_streets_" + event);
    // Set displayed event name
    eventStreetsElement.getElementsByClassName("event_name")[0].textContent = event;
    const entryContainer = eventStreetsElement.getElementsByClassName("list-group")[0];
    entryContainer.replaceChildren();
    for (const streetID in eventStreets) {
        const streetName = eventStreets[streetID];
        const entryItem = _streetsEntryTemplate.cloneNode(true);
        entryItem.append(streetID + ": " + streetName);
        entryItem.setAttribute("value", streetID);
        entryContainer.append(entryItem);
    }
}
function addStreet(_sender) {
    alert("Add unimplemented");
}
function removeStreet(_sender) {
    alert("Remove unimplemented");
}
async function sendStreets(edits) {
    const { err } = await fetchJsonNoThrow(url_streets, edits);
    if (err != null) {
        const message = `Failed to edit streets:\n${err}`;
        console.log(message);
        window.alert(message);
    }
}
