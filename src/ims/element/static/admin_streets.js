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
import * as ims from "./ims.js";
let eventDatas = [];
//
// Initialize UI
//
initAdminStreetsPage();
async function initAdminStreetsPage() {
    const initResult = await ims.commonPageInit();
    if (!initResult.authInfo.authenticated) {
        ims.redirectToLogin();
        return;
    }
    const eds = await initResult.eventDatas;
    if (eds == null) {
        console.error(`Failed to fetch events`);
        return;
    }
    eventDatas = eds;
    window.addStreet = addStreet;
    window.removeStreet = removeStreet;
    const { err } = await loadStreets();
    if (err == null) {
        drawStreets();
    }
}
let streets = {};
async function loadStreets() {
    const { json, err } = await ims.fetchJsonNoThrow(url_streets, null);
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
    for (const event of eventDatas) {
        const eventStreets = _streetsTemplate.cloneNode(true);
        // Add an id to the element for future reference
        eventStreets.id = `event_streets_${event.id}`;
        // Add to container
        container.append(eventStreets);
        updateEventStreets(event.id);
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
async function addStreet(sender) {
    const container = sender.closest(".event_streets");
    const event = container.getElementsByClassName("event_name")[0].textContent;
    const expression = sender.value.trim();
    const splitInd = expression.indexOf(":");
    if (splitInd === -1) {
        alert("Expected a ':' in the expression");
        return;
    }
    // e.g. "123: Abraham Ave" becomes "123" and "Abraham Ave"
    const id = expression.substring(0, splitInd);
    const name = expression.substring(splitInd + 1).trim();
    const edits = {};
    edits[event] = {};
    edits[event][id] = name;
    const { err } = await sendStreets(edits);
    await loadStreets();
    updateEventStreets(event);
    if (err != null) {
        ims.controlHasError(sender);
        return;
    }
    else {
        ims.controlHasSuccess(sender, 1000);
    }
    sender.value = "";
}
function removeStreet(_sender) {
    alert("Remove is unsupported for streets. Do this via SQL instead.");
}
async function sendStreets(edits) {
    const { err } = await ims.fetchJsonNoThrow(url_streets, {
        body: JSON.stringify(edits),
    });
    if (err != null) {
        const message = `Failed to edit streets:\n${err}`;
        console.log(message);
        window.alert(message);
        return { err: err };
    }
    return { err: null };
}
