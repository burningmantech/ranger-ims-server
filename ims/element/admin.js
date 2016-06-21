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

function initAdminPage() {
    function loadedAccessControlList() {
        drawEventAccess();
    }

    function loadedBody() {
        loadAccessControlList(loadedAccessControlList);
    }

    loadBody(loadedBody);
}


var accessControlList = null

function loadAccessControlList(success) {
    var url = accessURL;

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

    jsonRequest(url, null, ok, fail);
}


var _accessTemplate = null;

function drawEventAccess() {
    var container = $("#event_access_container");

    if (_accessTemplate == null) {
        _accessTemplate = container.children(".event_access:first");
    }

    container.empty();

    for (var i in events) {
        event = events[i];

        eventACL = accessControlList[event];

        if (eventACL == undefined) {
            continue;
        }

        modes = ["readers", "writers"];

        for (var i in modes) {
            mode = modes[i];

            eventAccess = $(_accessTemplate).clone();

            // Add an id to the element for future reference
            eventAccess.attr("id", "event_access_" + event);

            // Set displayed event name and mode
            eventAccess.find(".event_name").text(event);
            eventAccess.find(".access_mode").text(mode);

            entryContainer = eventAccess.find(".list-group:first");
            entryTemplate = entryContainer.children(".list-group-item:first");

            entryContainer.empty();

            for (var i in eventACL[mode]) {
                var expression = eventACL[mode][i];
                var entryItem = entryTemplate.clone();

                entryItem.append(expression);
                entryItem.attr("value", expression);

                entryContainer.append(entryItem);
            }

            // Add to container
            container.append(eventAccess);
        }
    }
}
