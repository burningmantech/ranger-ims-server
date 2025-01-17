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

function initPage() {
    function loadedAccessControlList() {
        drawAccess();
    }

    detectTouchDevice();
    loadAccessControlList(loadedAccessControlList);
}


let accessControlList = null

function loadAccessControlList(success) {
    function ok(data, status, xhr) {
        accessControlList = data;

        if (success) {
            success();
        }
    }

    function fail(error, status, xhr) {
        const message = "Failed to load access control list:\n" + error
        console.error(message);
        window.alert(message);
    }

    jsonRequest(url_acl, null, ok, fail);
}


let _accessTemplate = null;
let _entryTemplate = null;

let accessModes = ["readers", "writers", "reporters"];

function drawAccess() {
    const container = $("#event_access_container");

    if (_accessTemplate == null) {
        _accessTemplate = container.children(".event_access:first");

        _entryTemplate = _accessTemplate
            .find(".list-group:first")
            .children(".list-group-item:first")
            ;
    }

    container.empty();

    for (const event of events) {
        for (const mode of accessModes) {
            const eventAccess = $(_accessTemplate).clone();

            // Add an id to the element for future reference
            eventAccess.attr("id", "event_access_" + event + "_" + mode);

            // Add to container
            container.append(eventAccess);

            updateEventAccess(event, mode);
        }
    }
}


function updateEventAccess(event, mode) {
    const eventACL = accessControlList[event];

    if (eventACL == null) {
        return;
    }

    const eventAccess = $("#event_access_" + event + "_" + mode);

    // Set displayed event name and mode
    eventAccess.find(".event_name").text(event);
    eventAccess.find(".access_mode").text(mode);

    const entryContainer = eventAccess.find(".list-group:first");

    entryContainer.empty();

    for (const expression of eventACL[mode]) {
        const entryItem = _entryTemplate.clone();

        entryItem.append(expression);
        entryItem.attr("value", expression);

        entryContainer.append(entryItem);
    }
}


function addEvent(sender) {
    const event = sender.value.trim();

    function refresh() {
        loadAccessControlList(drawAccess);
    }

    function ok(data, status, xhr) {
        refresh();
        sender.value = "";  // Clear input field
    }

    function fail(requestError, status, xhr) {
        const message = "Failed to add event:\n" + requestError
        console.log(message);
        refresh();
        controlHasError($(sender));
        window.alert(message);
    }

    jsonRequest(url_events, {"add": [event]}, ok, fail);
}


function addAccess(sender) {
    const container = $(sender).parents(".event_access:first");
    const event = container.find(".event_name:first").text();
    const mode = container.find(".access_mode:first").text();
    const newExpression = sender.value.trim();

    if (newExpression === "**") {
        const confirmed = confirm(
            "DANGER: double-wildcard '**' ACLs can permit access to any requestor, even " +
            "those who aren't logged in! You probably don't want this, except maybe for " +
            "local testing.\n\n" +
            "By comparison, a single-wildcard '*' ACL grants access to any " +
            "authenticated user. You might be looking for that instead.\n\n" +
            "Proceed with firing footgun?"
        );
        if (!confirmed) {
            sender.value = "";
            return;
        }
    }

    const validExpression = newExpression === "**" || newExpression === "*" ||
        newExpression.startsWith("person:") || newExpression.startsWith("position:");
    if (!validExpression) {
        const confirmed = confirm(
            "WARNING: '" + newExpression + "' does not look like a valid ACL " +
            "expression. Example expressions include 'person:Hubcap' for an individual " +
            "or 'position:007' for a role. Wildcards are valid too, e.g. '*'\n\n" +
            "Proceed with firing footgun?"
        );
        if (!confirmed) {
            sender.value = "";
            return;
        }
    }

    const acl = accessControlList[event][mode].slice();

    acl.push(newExpression);

    const edits = {};
    edits[event] = {};
    edits[event][mode] = acl;

    function refresh() {
        for (const mode of accessModes) {
            updateEventAccess(event, mode);
        }
    }

    function ok() {
        loadAccessControlList(refresh);
        sender.value = "";  // Clear input field
    }

    function fail() {
        loadAccessControlList(refresh);
        controlHasError($(sender));
    }

    sendACL(edits, ok, fail);
}


function removeAccess(sender) {
    const container = $(sender).parents(".event_access:first");
    const event = container.find(".event_name:first").text();
    const mode = container.find(".access_mode:first").text();
    const expression = $(sender).parent().attr("value").trim();

    const acl = accessControlList[event][mode].slice();

    if (acl.indexOf(expression) < 0) {
        console.error("no such ACL: " + expression);
        return;
    }

    acl.splice(acl.indexOf(expression), 1);

    const edits = {};
    edits[event] = {};
    edits[event][mode] = acl;

    function refresh() {
        for (const mode of accessModes) {
            updateEventAccess(event, mode);
        }
    }

    function ok() {
        loadAccessControlList(refresh);
    }

    function fail() {
        loadAccessControlList(refresh);
    }

    sendACL(edits, ok, fail);
}


function sendACL(edits, success, error) {
    function ok(data, status, xhr) {
        success();
    }

    function fail(requestError, status, xhr) {
        const message = "Failed to edit ACL:\n" + requestError;
        console.log(message);
        error();
        window.alert(message);
    }

    jsonRequest(url_acl, edits, ok, fail);
}
