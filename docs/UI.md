# UI and API

## UI

The UI is served locally at http://127.0.0.1:5000.

## Endpoints

### GET /

Renders the main UI page.

### GET /avatars

Returns the current avatar list.

Response:
```
{ "avatars": ["Avatar 1", "Avatar 2"] }
```

### POST /avatars

Adds an avatar name.

Request:
```
{ "name": "New Avatar" }
```

Response:
```
{ "ok": true, "avatars": ["Avatar 1", "New Avatar"] }
```

### DELETE /avatars

Removes an avatar name.

Request:
```
{ "name": "Avatar 1" }
```

Response:
```
{ "ok": true, "avatars": [] }
```

### POST /start

Creates the UI queue and launches automation.
The automation remains running to auto-download completed videos into `outputFiles/`
until all items are downloaded (Ctrl+C to stop).

Request:
```
{
  "project_name": "Project",
  "avatar": "Avatar 1",
  "config": { "quality": "720p", "fps": "25", "subtitles": "yes" },
  "items": [
    { "title": "Scene 1", "script": "Hello world" }
  ]
}
```

Response:
```
{ "ok": true, "pid": 12345 }
```
