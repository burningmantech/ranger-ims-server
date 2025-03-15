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
    const {err} = await loadStreets();
    if (err == null) {
        drawStreets();
    }
}

interface Streets {
    [index: number]: string,
}

interface EventStreets {
    [index: string]: Streets,
}


let streets: EventStreets = {};

async function loadStreets(): Promise<{err:string|null}> {
    let {json, err} = await fetchJsonNoThrow(url_streets, null);
    if (err != null) {
        const message = `Failed to load streets: ${err}`;
        console.error(message);
        window.alert(message);
        return {err: message};
    }
    streets = json;
    return {err: null};
}


let _streetsTemplate: any = null;
let _streetsEntryTemplate: any = null;

function drawStreets() {
    // @ts-ignore JQuery
    const container = $("#event_streets_container");

    if (_streetsTemplate == null) {
        _streetsTemplate = container.children(".event_streets:first");

        _streetsEntryTemplate = _streetsTemplate
            .find(".list-group:first")
            .children(".list-group-item:first")
            ;
    }

    container.empty();

    for (const event of events!) {
        // @ts-ignore JQuery
        const eventStreets = $(_streetsTemplate).clone();

        // Add an id to the element for future reference
        eventStreets.attr("id", "event_streets_" + event);

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

    // @ts-ignore JQuery
    const eventStreetsElement = $("#event_streets_" + event);

    // Set displayed event name
    eventStreetsElement.find(".event_name").text(event);

    const entryContainer = eventStreetsElement.find(".list-group:first");

    entryContainer.empty();

    for (const streetID in eventStreets) {
        const streetName = eventStreets[streetID];
        const entryItem = _streetsEntryTemplate.clone();

        entryItem.append(streetID + ": " + streetName);
        entryItem.attr("value", streetID);

        entryContainer.append(entryItem);
    }
}


function addStreet(sender) {
    alert("Add unimplemented");
}


function removeStreet(sender) {
    alert("Remove unimplemented");
}


async function sendStreets(edits) {
    let {err} = await fetchJsonNoThrow(url_streets, edits);
    if (err != null) {
        const message = `Failed to edit streets:\n${err}`;
        console.log(message);
        window.alert(message);
    }
}
