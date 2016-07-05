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

function initIncidentReportPage() {
    function loadedIncidentReport() {
    }

    function loadedBody() {
        disableEditing();
        loadAndDisplayIncidentReport(loadedIncidentReport);
    }

    loadBody(loadedBody);
}


//
// Load incident report
//

var incidentReport = null;

function loadIncidentReport(success) {
    var number = null;
    if (incidentReport == null) {
        // First time here.  Use page JavaScript initial value.
        number = incidentReportNumber;
    } else {
        // We have an incident already.  Use that number.
        number = incidentReport.number;
    }

    function ok(data, status, xhr) {
        incidentReport = data;

        if (success != undefined) {
            success();
        }
    }

    function fail(error, status, xhr) {
        disableEditing();
        var message = "Failed to load incident report:\n" + error;
        console.error(message);
        window.alert(message);
    }

    if (number == null) {
        ok({
            "number": null,
            "created": null,
        });
    } else {
        var url = incidentReportsURL + "/" + number;
        jsonRequest(url, null, ok, fail);
    }
}


function loadAndDisplayIncidentReport(success) {
    function loaded() {
        if (incidentReport == null) {
            var message = "Incident report failed to load";
            console.log(message);
            alert(message);
            return;
        }

        drawReportEntries(incidentReport.report_entries);
        $("#incident_report_add").on("input", reportEntryEdited);

        if (editingAllowed) {
            enableEditing();
        }

        if (success != undefined) {
            success();
        }
    }

    loadIncidentReport(loaded);
}
