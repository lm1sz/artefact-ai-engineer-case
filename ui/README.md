# Local web interface

The UI imports the same Python Agent and Tools as the CLI. Configure OpenAI `gpt-6.1-sol` and your own key using the root README, then run from the repository root:

```powershell
python -m ui.server --port 8765
```

Open http://127.0.0.1:8765. Sessions are guests unless the developer launches the server with `--demo-customer-id 3` for an authorized order demonstration. This is simulated identity, not a login; the browser cannot choose a customer id.

`server.py` serves the HTML/CSS/JavaScript and `/api/chat`, while the chatbot package owns source access and business rules. Keys stay on the server. History is held per browser session; “Nova conversa” resets it while preserving identity. No purchase, refund or ticket is executed.

The server binds to loopback, checks host/origin/CSRF and uses HttpOnly/SameSite cookies. User and model messages are rendered as text. Safe provider failures are displayed without invented answers; quota cooldown metadata prevents repeated sends. This local demonstration is not production authentication.

Run `python -m unittest discover -s ui/tests -v` for HTTP/session tests with a simulated provider. Opening index.html directly or using a static file server does not provide the Python chat endpoint.
