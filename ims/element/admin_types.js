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
    detectTouchDevice();
    loadAndDrawIncidentTypes();
}


function loadAndDrawIncidentTypes() {
    function loadedIncidentTypes() {
        drawIncidentTypes();
    }

    loadIncidentTypes(loadedIncidentTypes);
}


var incidentTypes = null;
var incidentTypesVisible = null;

function loadIncidentTypes(success) {
    var url = incidentTypesURL;

    var gotAll = false;
    var gotVisible = false;

    function ok() {
        if (gotAll && gotVisible) {
            if (success != undefined) {
                success();
            }
        }
    }

    function okVisible(data, status, xhr) {
        incidentTypesVisible = data;
        gotVisible = true;
        ok();
    }


    function okAll(data, status, xhr) {
        incidentTypes = data;
        gotAll = true;
        ok();
    }

    function fail(error, status, xhr) {
        var message = "Failed to load incident types:\n" + error
        console.error(message);
        window.alert(message);
    }

    jsonRequest(incidentTypesURL, null, okVisible, fail);
    jsonRequest(incidentTypesURL + "/?hidden=true", null, okAll, fail);
}


var _incidentTypesTemplate = null;
var _entryTemplate = null;

function drawIncidentTypes() {
    var container = $("#incident_types_container");

    if (_incidentTypesTemplate == null) {
        _incidentTypesTemplate = container.children(".incident_types:first");

        _entryTemplate = _incidentTypesTemplate
            .find(".list-group:first")
            .children(".list-group-item:first")
            ;
    }

    updateIncidentTypes();
}


function updateIncidentTypes() {
    var incidentTypesElement = $("#incident_types");

    var entryContainer = incidentTypesElement.find(".list-group:first");

    entryContainer.empty();

    for (var i in incidentTypes) {
        var incidentType = incidentTypes[i];
        var entryItem = _entryTemplate.clone();

        if (incidentTypesVisible.indexOf(incidentType) == -1) {
            entryItem.addClass("item-hidden")
        } else {
            entryItem.addClass("item-visible")
        }

        entryItem.append(incidentType);
        entryItem.attr("value", incidentType);

        entryContainer.append(entryItem);
    }
}


function addIncidentType(sender) {
    function ok () {
        sender.value = "";
        loadAndDrawIncidentTypes();
    }

    sendIncidentTypes(
        { "add": [sender.value] },
        ok, loadAndDrawIncidentTypes
    );
}


function removeIncidentType(sender) {
    alert("Remove unimplemented");
}


function showIncidentType(sender) {
    sendIncidentTypes(
        { "show": [$(sender).parent().attr("value")] },
        loadAndDrawIncidentTypes, loadAndDrawIncidentTypes
    );
}


function hideIncidentType(sender) {
    sendIncidentTypes(
        { "hide": [$(sender).parent().attr("value")] },
        loadAndDrawIncidentTypes, loadAndDrawIncidentTypes
    );
}


function sendIncidentTypes(edits, success, error) {
    function ok(data, status, xhr) {
        success();
    }

    function fail(requestError, status, xhr) {
        var message = "Failed to edit incident types:\n" + requestError
        console.log(message);
        error();
        window.alert(message);
    }

    jsonRequest(incidentTypesURL + "/", edits, ok, fail);
}
