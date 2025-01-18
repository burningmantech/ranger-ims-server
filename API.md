# API

Available REST API endpoints.

## /ims/api/ping/

## /ims/api/bag/

## /ims/api/auth/

Get a JWT token for endpoints that require auth.

### POST

```
{
	"identification": "<handle or email>",
	"password": "<password>"
}
```

### Expected POST Response

```
{
	"token": "<token>"
}
```

### JWT Token Contents

```
{
  "exp": 1737165463,
  "iat": 1737161863,
  "iss": "ranger-ims-server",
  "preferred_username": "HubCap",
  "ranger_on_site": true,
  "ranger_positions": "HQ Window,Dirt - Green Dot,Tow Truck Driver,Tech Ops,Green Dot Sanctuary,Tow Truck Mentee,DPW Ranger,Tech On Call,Fire Lane,NVO Ranger,DPW Ranger On Call,Tech Ops - Pre-Event,Tow Truck Ride Along",
  "sub": "HubCap"
}
```

## /ims/api/access/

## /ims/api/streets/

## /ims/api/personnel/

Auth Required

Responds with a list of personnel.

### GET

```
{
	"identification": "<handle or email>",
	"password": "<password>"
}
```

### Expected Response

```
{
	"token": "<token>"
}
```

## /ims/api/incident_types/

## /ims/api/events/

## /ims/api/event/

## /ims/api/incidents/

## /ims/api/incident/

## /ims/api/field_reports/

## /ims/api/field_report/

## /ims/api/event_source/