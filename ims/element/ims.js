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
// HTML encoding
//

// **** BEGIN WEAKNESS ***

// It seems ridiculous that this isn't standard in JavaScript
// It is certainly ridiculous to involve the DOM, but on the other hand, the
// browser will implement this correctly, and any solution using .replace()
// will be buggy.  And this will be fast.  But still, this is weak.

var _domTextAreaForHaxxors = document.createElement("textarea")

function textAsHTML(text) {
  _domTextAreaForHaxxors.textContent = text;
  return _domTextAreaForHaxxors.innerHTML;
}

function htmlAsText(html) {
  _domTextAreaForHaxxors.innerHTML = html;
  return _domTextAreaForHaxxors.textContent;
}

// **** END WEAKNESS ***


//
// Generic string formatting
//

function padTwo(segment) {
  if (segment == undefined) {
    return "?";
  }

  segment = segment.toString();

  if (segment.length == 1) {
    return "0" + segment;
  }

  return "" + segment;
}


function shortFormatDate(date) {
  return moment(date).format("M/D@h:mm z");
}


//
// Incident data
//

function priorityNameFromNumber(priorityNumber) {
  // priorityNumber should be an int, 1-5.

  switch (priorityNumber) {
    case 1: return "High";
    case 2: return "High";
    case 3: return "Normal";
    case 4: return "Low";
    case 5: return "Low︎";
    default:
      console.warn("Unknown incident priority number: " + priorityNumber);
      return undefined;
  }
}


function priorityIconFromNumber(priorityNumber) {
  // priorityNumber should be an int, 1-5.

  switch (priorityNumber) {
    case 1: return '<span class="glyphicon glyphicon-arrow-up">';
    case 2: return '<span class="glyphicon glyphicon-arrow-up">';
    case 3: return '<span class="glyphicon glyphicon-minus">';
    case 4: return '<span class="glyphicon glyphicon-arrow-down">';
    case 5: return '<span class="glyphicon glyphicon-arrow-down">';
    default:
      console.warn("Unknown incident priority number: " + priorityNumber);
      return undefined;
  }
}


function stateNameFromID(stateID) {
  // stateID should be a string key.

  switch (stateID) {
    case "new"       : return "New";
    case "on_hold"   : return "On Hold";
    case "dispatched": return "Dispatched";
    case "on_scene"  : return "On Scene";
    case "closed"    : return "Closed";
    default:
      console.warn("Unknown incident state ID: " + stateID);
      return undefined;
  }
}


function stateSortKeyFromID(stateID) {
  // stateID should be a string key.

  switch (stateID) {
    case "new"       : return 1;
    case "on_hold"   : return 2;
    case "dispatched": return 3;
    case "on_scene"  : return 4;
    case "closed"    : return 5;
    default:
      console.warn("Unknown incident state ID: " + stateID);
      return undefined;
  }
}


function concentricStreetFromID(streetID) {
  // streetID should be an int

  if (streetID == undefined) {
    return undefined;
  }

  var name = concentricStreetNameByNumber[streetID];
  if (name == undefined) {
    console.warn("Unknown street ID: " + streetID);
    name = undefined;
  }
  return name;
}


function stateForIncident(incident) {
  // Data from 2014+ should have incident.state set.
  if (incident.state != undefined) {
    return incident.state;
  }

  // 2013 data had multiple overloaded timestamps instead.
  if (incident.closed != undefined) {
    return "closed";
  }
  if (incident.on_scene != undefined) {
    return "on_scene";
  }
  if (incident.dispatched != undefined) {
    return "dispatched";
  }
  if (incident.created != undefined) {
    return "new";
  }

  console.warn("Unknown state for incident: " + incident);
  return undefined;
}


function summarizeIncident(incident) {
  var summary = incident.summary;
  var reportEntries = incident.report_entries;

  if (summary == undefined) {
    if (reportEntries == undefined) {
      console.warn("No summary provided.");
      return "";
    }
    else {
      // Get the first line of the first report entry.
      for (var i in reportEntries) {
        var lines = reportEntries[i].text.split("\n");

        for (var j in lines) {
          var line = lines[j];
          if (line != undefined && line != "") {
            return summary;
          }
        }
      }
    }

    console.warn("No summary provided and no report entry text.");
    return "";
  }

  return summary;
}


function reportTextFromIncident(incident) {
  var texts = [];

  if (incident.summary != undefined) {
    texts.push(incident.summary);
  }

  var reportEntries = incident.report_entries;

  for (var i in reportEntries) {
    var reportEntry = reportEntries[i];

    // Skip system entries
    if (reportEntry.system_entry) {
      continue;
    }

    var text = reportEntry.text;

    if (text != undefined) {
      texts.push(text);
    }
  }

  var text = texts.join("");

  return text;
}


function shortDescribeLocation(location) {
  if (location == undefined) {
    return undefined;
  }

  var locationBits = [];

  if (location.name != undefined) {
    locationBits.push(location.name);
  }

  switch (location.type) {
    case undefined:
      // Fall through to "text" case
    case "text":
      break;
    case "garett":
      locationBits.push(" (");
      locationBits.push(padTwo(location.radial_hour));
      locationBits.push(":");
      locationBits.push(padTwo(location.radial_minute));
      locationBits.push("@");
      locationBits.push(concentricStreetFromID(location.concentric));
      locationBits.push(")");
      break;
    default:
      locationBits.push(
        "Unknown location type:" + location.type
      );
      break;
  }

  return locationBits.join("");
}


//
// DataTables rendering
//

function renderPriority(priorityNumber, type, incident) {
  switch (type) {
    case "display":
      return priorityIconFromNumber(priorityNumber);
    case "filter":
      return priorityNameFromNumber(priorityNumber);
    case "type":
    case "sort":
      return priorityNumber;
  }
  return undefined;
}

function renderDate(date, type, incident) {
  switch (type) {
    case "display":
      return textAsHTML(shortFormatDate(date));
    case "filter":
      return shortFormatDate(date);
    case "type":
    case "sort":
      return moment(date);
  }
  return undefined;
}

function renderState(state, type, incident) {
  if (state == undefined) {
    state = stateForIncident(incident);
  }

  switch (type) {
    case "display":
      return textAsHTML(stateNameFromID(state));
    case "filter":
      return stateNameFromID(state);
    case "type":
      return state;
    case "sort":
      return stateSortKeyFromID(state);
  }
  return undefined;
}

function renderLocation(data, type, incident) {
  if (data == undefined) {
    data = "";
  }
  switch (type) {
    case "display":
      return textAsHTML(shortDescribeLocation(data));
    case "filter":
    case "sort":
      return shortDescribeLocation(data);
    case "type":
      return "";
  }
  return undefined;
}

function renderSummary(data, type, incident) {
  switch (type) {
    case "display":
      return textAsHTML(summarizeIncident(incident));
    case "sort":
      return summarizeIncident(incident);
    case "filter":
      return reportTextFromIncident(incident);
    case "type":
      return "";
  }
  return undefined;
}
