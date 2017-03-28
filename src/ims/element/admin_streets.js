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
    function loadedStreets() {
        drawStreets();
    }

    detectTouchDevice();
    loadStreets(loadedStreets);
}


var streets = null;

function loadStreets(success) {
    var url = streetsURL;

    function ok(data, status, xhr) {
        streets = data;

        if (success != undefined) {
            success();
        }
    }

    function fail(error, status, xhr) {
        var message = "Failed to load streets:\n" + error
        console.error(message);
        window.alert(message);
    }

    jsonRequest(streetsURL, null, ok, fail);
}


var _streetsTemplate = null;
var _entryTemplate = null;

function drawStreets() {
    var container = $("#event_streets_container");

    if (_streetsTemplate == null) {
        _streetsTemplate = container.children(".event_streets:first");

        _entryTemplate = _streetsTemplate
            .find(".list-group:first")
            .children(".list-group-item:first")
            ;
    }

    container.empty();

    for (var i in events) {
        var event = events[i];

        var eventStreets = $(_streetsTemplate).clone();

        // Add an id to the element for future reference
        eventStreets.attr("id", "event_streets_" + event);

        // Add to container
        container.append(eventStreets);

        updateEventStreets(event);
    }
}


function updateEventStreets(event) {
    var eventStreets = streets[event];

    if (eventStreets == undefined) {
        return;
    }

    var eventStreetsElement = $("#event_streets_" + event);

    // Set displayed event name
    eventStreetsElement.find(".event_name").text(event);

    var entryContainer = eventStreetsElement.find(".list-group:first");

    entryContainer.empty();

    for (var streetID in eventStreets) {
        var streetName = eventStreets[streetID];
        var entryItem = _entryTemplate.clone();

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


function sendStreets(edits, success, error) {
    function ok(data, status, xhr) {
        success();
    }

    function fail(requestError, status, xhr) {
        var message = "Failed to edit streets:\n" + requestError
        console.log(message);
        error();
        window.alert(message);
    }

    jsonRequest(streetsURL, edits, ok, fail);
}
