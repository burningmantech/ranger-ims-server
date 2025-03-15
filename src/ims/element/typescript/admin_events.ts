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

async function initAdminEventsPage(): Promise<void> {
    detectTouchDevice();
    await loadAccessControlList();
    drawAccess();
}

enum Validity {
    always = "always",
    onsite = "onsite",
}

interface Access {
    expression: string;
    validity: Validity;
}

interface EventAccess {
    // key is access mode ("readers", "writers", "reporters")
    [index: string]: Access[];
}

interface EventsAccess {
    [index: string]: EventAccess | null;
}

let accessControlList: EventsAccess|null = null;

async function loadAccessControlList() : Promise<{err: string|null}> {
    let {json, err} = await fetchJsonNoThrow(url_acl, null);
    if (err != null) {
        const message = `Failed to load access control list: ${err}`;
        console.error(message);
        window.alert(message);
        return {err: message};
    }
    accessControlList = json;
    return {err: null};
}


let _accessTemplate : HTMLCollection|null = null;
let _eventsEntryTemplate : HTMLCollection|null = null;

let accessModes: string[] = ["readers", "writers", "reporters"];

function drawAccess(): void {
    // @ts-ignore JQuery
    const container = $("#event_access_container");

    if (_accessTemplate == null) {
        _accessTemplate = container.children(".event_access:first");

        _eventsEntryTemplate = _accessTemplate!
            // @ts-ignore JQuery
            .find(".list-group:first")
            .children(".list-group-item:first")
            ;
    }

    container.empty();

    if (accessControlList == null) {
        return;
    }
    const events: string[] = Object.keys(accessControlList);
    for (const event of events) {
        for (const mode of accessModes) {
            // @ts-ignore JQuery
            const eventAccess = $(_accessTemplate).clone();

            // Add an id to the element for future reference
            eventAccess.attr("id", "event_access_" + event + "_" + mode);

            // Add to container
            container.append(eventAccess);

            updateEventAccess(event, mode);
        }
    }
}


function updateEventAccess(event: string, mode: string): void {
    if (accessControlList == null) {
        return;
    }
    const eventACL: EventAccess|null = accessControlList[event];
    if (eventACL == null) {
        return;
    }

    // @ts-ignore JQuery
    const eventAccess = $("#event_access_" + event + "_" + mode);

    // Set displayed event name and mode
    eventAccess.find(".event_name").text(event);
    eventAccess.find(".access_mode").text(mode);

    const entryContainer = eventAccess.find(".list-group:first");

    entryContainer.empty();

    for (const accessEntry of eventACL[mode]) {
        // @ts-ignore JQuery
        const entryItem = _eventsEntryTemplate.clone();

        entryItem.append(accessEntry.expression);
        entryItem.attr("value", accessEntry.expression);
        entryItem.find(".access_validity").val(accessEntry.validity);

        entryContainer.append(entryItem);
    }
}


async function addEvent(sender: HTMLInputElement): Promise<void> {
    const event = sender.value.trim();
    const {err} = await fetchJsonNoThrow(url_events, {
        body: JSON.stringify({
            "add": [event],
        }),
    });
    if (err != null) {
        const message = `Failed to add event: ${err}`;
        console.log(message);
        window.alert(message);
        await loadAccessControlList();
        drawAccess();
        // @ts-ignore JQuery
        controlHasError($(sender));
        return;
    }
    await loadAccessControlList();
    drawAccess();
    sender.value = "";  // Clear input field
}


async function addAccess(sender: HTMLInputElement): Promise<void> {
    // @ts-ignore JQuery
    const container = $(sender).parents(".event_access:first");
    const event = container.find(".event_name:first").text();
    const mode = container.find(".access_mode:first").text();
    const newExpression = sender.value.trim();

    if (newExpression === "**") {
        const confirmed = confirm(
            "Double-wildcard '**' ACLs are no longer supported, so this ACL will have " +
            "no effect.\n\n" +
            "Proceed with doing something pointless?"
        );
        if (!confirmed) {
            sender.value = "";
            return;
        }
    }

    const validExpression = newExpression === "**" || newExpression === "*" ||
        newExpression.startsWith("person:") || newExpression.startsWith("position:") || newExpression.startsWith("team:");
    if (!validExpression) {
        const confirmed = confirm(
            "WARNING: '" + newExpression + "' does not look like a valid ACL " +
            "expression. Example expressions include 'person:Hubcap' for an individual, " +
            "'position:007' for a role, and 'team:Council' for a team. Wildcards are " +
            "supported as well, e.g. '*'\n\n" +
            "Proceed with firing footgun?"
        );
        if (!confirmed) {
            sender.value = "";
            return;
        }
    }

    const acl: Access[] = accessControlList![event]![mode].slice();

    const newVal: Access = {
        "expression": newExpression,
        "validity": Validity.always,
    };

    acl.push(newVal);

    const edits: EventsAccess = {};
    edits[event] = {};
    edits[event][mode] = acl;

    const {err} = await sendACL(edits);
    await loadAccessControlList();
    for (const mode of accessModes) {
        updateEventAccess(event, mode);
    }
    if (err != null) {
        // @ts-ignore JQuery
        controlHasError($(sender));
        return;
    }
    sender.value = "";  // Clear input field
}


async function removeAccess(sender: HTMLButtonElement): Promise<void> {
    // @ts-ignore JQuery
    const container = $(sender).parents(".event_access:first");
    const event = container.find(".event_name:first").text();
    const mode = container.find(".access_mode:first").text();
    // @ts-ignore JQuery
    const expression = $(sender).parent().attr("value").trim();

    const acl: Access[] = accessControlList![event]![mode].slice();

    let foundIndex: number = -1;
    for (const i in acl) {
        if (acl[i].expression === expression) {
            foundIndex = parseInt(i);
            break;
        }
    }
    if (foundIndex < 0) {
        console.error("no such ACL: " + expression);
        return;
    }

    acl.splice(foundIndex, 1);

    const edits: EventsAccess = {};
    edits[event] = {};
    edits[event][mode] = acl;

    await sendACL(edits);
    await loadAccessControlList();
    for (const mode of accessModes) {
        updateEventAccess(event, mode);
    }
}

async function setValidity(sender: HTMLSelectElement): Promise<void> {
    // @ts-ignore JQuery
    const container = $(sender).parents(".event_access:first");
    const event = container.find(".event_name:first").text();
    const mode = container.find(".access_mode:first").text();
    // @ts-ignore JQuery
    const expression = $(sender).parent().attr("value").trim();

    const acl: Access[] = accessControlList![event]![mode].slice();

    const newVal: Access = {
        "expression": expression,
        "validity": sender.value === "onsite" ? Validity.onsite : Validity.always,
    };

    acl.push(newVal);

    const edits: EventsAccess = {};
    edits[event] = {};
    edits[event][mode] = acl;

    const {err} = await sendACL(edits);
    await loadAccessControlList();
    for (const mode of accessModes) {
        updateEventAccess(event, mode);
    }
    if (err != null) {
        // @ts-ignore JQuery
        controlHasError($(sender));
        return;
    }
    sender.value = "";  // Clear input field
}


async function sendACL(edits: EventsAccess): Promise<{err:string|null}> {
    const {err} = await fetchJsonNoThrow(url_acl, {
        body: JSON.stringify(edits),
    });
    if (err == null) {
        return {err: null};
    }
    const message = `Failed to edit ACL:\n${JSON.stringify(err)}`;
    console.log(message);
    window.alert(message);
    return {err: err};
}
