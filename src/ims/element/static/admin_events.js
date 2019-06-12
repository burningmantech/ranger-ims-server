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


var accessControlList = null

function loadAccessControlList(success) {
    function ok(data, status, xhr) {
        accessControlList = data;

        if (success != undefined) {
            success();
        }
    }

    function fail(error, status, xhr) {
        var message = "Failed to load access control list:\n" + error
        console.error(message);
        window.alert(message);
    }

    jsonRequest(url_acl, null, ok, fail);
}


var _accessTemplate = null;
var _entryTemplate = null;

var accessModes = ["readers", "writers", "reporters"];

function drawAccess() {
    var container = $("#event_access_container");

    if (_accessTemplate == null) {
        _accessTemplate = container.children(".event_access:first");

        _entryTemplate = _accessTemplate
            .find(".list-group:first")
            .children(".list-group-item:first")
            ;
    }

    container.empty();

    for (var i in events) {
        var event = events[i];

        for (var i in accessModes) {
            var mode = accessModes[i];

            var eventAccess = $(_accessTemplate).clone();

            // Add an id to the element for future reference
            eventAccess.attr("id", "event_access_" + event + "_" + mode);

            // Add to container
            container.append(eventAccess);

            updateEventAccess(event, mode);
        }
    }
}


function updateEventAccess(event, mode) {
    var eventACL = accessControlList[event];

    if (eventACL == undefined) {
        return;
    }

    var eventAccess = $("#event_access_" + event + "_" + mode);

    // Set displayed event name and mode
    eventAccess.find(".event_name").text(event);
    eventAccess.find(".access_mode").text(mode);

    var entryContainer = eventAccess.find(".list-group:first");

    entryContainer.empty();

    for (var i in eventACL[mode]) {
        var expression = eventACL[mode][i];
        var entryItem = _entryTemplate.clone();

        entryItem.append(expression);
        entryItem.attr("value", expression);

        entryContainer.append(entryItem);
    }
}


function addEvent(sender) {
    var event = sender.value.trim();

    function refresh() {
        loadAccessControlList(drawAccess);
    }

    function ok(data, status, xhr) {
        refresh();
        sender.value = "";  // Clear input field
    }

    function fail(requestError, status, xhr) {
        var message = "Failed to add event:\n" + requestError
        console.log(message);
        refresh();
        controlHasError($(sender));
        window.alert(message);
    }

    jsonRequest(url_events, {"add": [event]}, ok, fail);
}


function addAccess(sender) {
    var container = $(sender).parents(".event_access:first");
    var event = container.find(".event_name:first").text();
    var mode = container.find(".access_mode:first").text();
    var newExpression = sender.value.trim();

    var acl = accessControlList[event][mode].slice();

    acl.push(newExpression);

    edits = {};
    edits[event] = {};
    edits[event][mode] = acl;

    function refresh() {
        for (var i in accessModes) {
            updateEventAccess(event, accessModes[i]);
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
    var container = $(sender).parents(".event_access:first");
    var event = container.find(".event_name:first").text();
    var mode = container.find(".access_mode:first").text();
    var expression = $(sender).parent().text().trim();

    var acl = accessControlList[event][mode].slice();

    acl.splice(acl.indexOf(expression), 1);

    edits = {};
    edits[event] = {};
    edits[event][mode] = acl;

    function refresh() {
        for (var i in accessModes) {
            updateEventAccess(event, accessModes[i]);
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
        var message = "Failed to edit ACL:\n" + requestError
        console.log(message);
        error();
        window.alert(message);
    }

    jsonRequest(url_acl, edits, ok, fail);
}
