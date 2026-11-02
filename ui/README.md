# UI prototype

Open `index.html` directly, or run from the repository root:

```powershell
py -3 -m http.server 8765 --bind 127.0.0.1 --directory ui
```

Visit `http://127.0.0.1:8765`.

This is a standalone visual prototype with scripted responses and generic product illustrations. It has no model calls, authentication, order access or backend connection. Price examples come from `chatbot/examples/reference/`. Chat content is not transmitted or persisted. Google Fonts is optional.

A future integration should call the Python agent through a server endpoint with verified session identity. Keep API keys on the server.
