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

interface EventsStreets {
    // key is event name
    [index: string]: Streets,
}

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

let streets: EventsStreets = {};

async function loadStreets(): Promise<{err:string|null}> {
    const {json, err} = await fetchJsonNoThrow<EventsStreets>(url_streets, null);
    if (err != null) {
        const message = `Failed to load streets: ${err}`;
        console.error(message);
        window.alert(message);
        return {err: message};
    }
    streets = json!;
    return {err: null};
}


let _streetsTemplate: HTMLDivElement|null = null;
let _streetsEntryTemplate: HTMLLIElement |null = null;

function drawStreets(): void {
    const container: HTMLElement = document.getElementById("event_streets_container")!;
    if (_streetsTemplate == null) {
        _streetsTemplate = container.querySelectorAll<HTMLDivElement>(".event_streets")[0]!;
        _streetsEntryTemplate = _streetsTemplate.querySelector("ul")!.querySelector("li");
    }

    container.replaceChildren();

    for (const event of events!) {
        const eventStreets = _streetsTemplate.cloneNode(true) as HTMLDivElement;

        // Add an id to the element for future reference
        eventStreets.id = `event_streets_${event}`;

        // Add to container
        container.append(eventStreets);

        updateEventStreets(event);
    }
}


function updateEventStreets(event: string) {
    const eventStreets = streets[event];

    if (eventStreets == null) {
        return;
    }

    const eventStreetsElement: HTMLElement = document.getElementById("event_streets_" + event)!;

    // Set displayed event name
    eventStreetsElement.getElementsByClassName("event_name")[0]!.textContent = event;

    const entryContainer: Element = eventStreetsElement.getElementsByClassName("list-group")[0]!;

    entryContainer.replaceChildren();

    for (const streetID in eventStreets) {
        const streetName = eventStreets[streetID];
        const entryItem = _streetsEntryTemplate!.cloneNode(true) as HTMLElement;

        entryItem.append(streetID + ": " + streetName);
        entryItem.setAttribute("value", streetID);

        entryContainer.append(entryItem);
    }
}


async function addStreet(sender: HTMLInputElement): Promise<void> {
    const container: HTMLElement = sender.closest(".event_streets")!;
    const event = container.getElementsByClassName("event_name")[0]!.textContent!;

    const expression = sender.value.trim();
    const splitInd = expression.indexOf(":");
    if (splitInd === -1) {
        alert("Expected a ':' in the expression");
        return;
    }
    // e.g. "123: Abraham Ave" becomes "123" and "Abraham Ave"
    const id = expression.substring(0, splitInd);
    const name = expression.substring(splitInd+1).trim();

    const edits: EventsStreets = {};
    edits[event] = {};
    edits[event][id] = name;

    const {err} = await sendStreets(edits);
    await loadStreets();
    updateEventStreets(event);
    if (err != null) {
        controlHasError(sender);
        return;
    } else {
        controlHasSuccess(sender, 1000);
    }
    sender.value = "";
}


function removeStreet(_sender: HTMLInputElement): void {
    alert("Remove is unsupported for streets. Do this via SQL instead.");
}


async function sendStreets(edits: EventsStreets): Promise<{err: string|null}> {
    const {err} = await fetchJsonNoThrow(url_streets, {
        body: JSON.stringify(edits),
    });
    if (err != null) {
        const message = `Failed to edit streets:\n${err}`;
        console.log(message);
        window.alert(message);
        return {err: err};
    }
    return {err: null};
}
