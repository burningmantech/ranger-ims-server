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


// FIXME: Try out momentjs: http://momentjs.com/docs/
function shortFormatDate(date) {
  return (
    padTwo(date.getMonth() + 1) + "/" +
    padTwo(date.getDate())      + "@" +
    padTwo(date.getHours())     + ":" +
    padTwo(date.getMinutes())
  );
}


//
// Incident data
//

function priorityNameFromNumber(priorityNumber) {
  // priorityNumber should be an int, 1-5.

  switch (priorityNumber) {
    case 1: return "⬆︎";
    case 2: return "⬆︎";
    case 3: return "•";
    case 4: return "⬇︎";
    case 5: return "⬇︎";
    default:
      console.log("Unknown incident priority number: " + priorityNumber);
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
      console.log("Unknown incident state ID: " + stateID);
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
      console.log("Unknown incident state ID: " + stateID);
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
    console.log("Unknown street ID: " + streetID);
    name = undefined;
  }
  return name;
}


function summarizeIncident(incident) {
  var summary = incident.summary;
  var reportEntries = incident.report_entries;

  if (summary == undefined) {
    if (reportEntries == undefined) {
      console.log("No summary provided.");
      return "";
    }
    else {
      // Get the first line of the first report entry.
      for (var i in reportEntries) {
        var lines = reportEntries[i].text.split("\n");

        for (var j in lines) {
          var line = lines[j];
          if (line == undefined || line == "") {
            continue;
          }
          summary = line;
          break;
        }

        if (summary != undefined) {
          break;
        }
      }

      return summary;
    }

    console.log("No summary provided and no report entry text.");
    return "";
  }

  return summary;
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
    case "filter":
      return textAsHTML(priorityNameFromNumber(priorityNumber));
    case "type":
    case "sort":
      return priorityNumber;
  }
  return undefined;
}

function renderDate(date, type, incident) {
  switch (type) {
    case "display":
    case "filter":
      return textAsHTML(shortFormatDate(date));
    case "type":
    case "sort":
      return date;
  }
  return undefined;
}

function renderState(state, type, incident) {
  switch (type) {
    case "display":
    case "filter":
    case "type":
      return textAsHTML(stateNameFromID(state));
    case "sort":
      return stateSortKeyFromID(state);
  }
  return undefined;
}

function renderLocation(data, type, incident) {
  switch (type) {
    case "display":
    case "filter":
    case "type":
    case "sort":
      return textAsHTML(shortDescribeLocation(data));
  }
  return undefined;
}

function renderSummary(data, type, incident) {
  switch (type) {
    case "display":
    case "filter":
    case "type":
    case "sort":
      return textAsHTML(summarizeIncident(incident));
  }
  return undefined;
}
