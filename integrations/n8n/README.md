# n8n Integration

This integration connects the local voice assistant to [n8n](https://n8n.io/) workflow automation, enabling the LLM to trigger real-world actions via function calling.

## How It Works

```
User speaks → STT → LLM (with tools) → function call → n8n webhook → action → response → TTS → Speaker
```

1. The LLM is configured with tool definitions (OpenAI function-calling format)
2. When the LLM decides to call a tool, the `ToolsService` intercepts it
3. It sends an HTTP POST to the corresponding n8n webhook URL with the function parameters
4. n8n executes the workflow (e.g., control lights, query calendar)
5. The response is fed back to the LLM to generate a natural language reply

## Setup

### 1. Install n8n

```bash
docker run -d --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n n8nio/n8n
```

### 2. Import Workflows

Import the example workflows from `example_workflows/` into your n8n instance:
- Open n8n at http://localhost:5678
- Go to Workflows → Import from File
- Import each JSON file

### 3. Activate Webhooks

Each workflow uses a Webhook trigger node. After importing:
1. Open the workflow
2. Click "Active" toggle to enable it
3. Note the webhook URL (shown in the Webhook node)

### 4. Configure Paths

Update `config.yaml` with your webhook paths:

```yaml
n8n:
  base_url: http://localhost:5678
  webhooks:
    control_smart_home: /webhook/smart-home
    query_calendar: /webhook/calendar
    send_message: /webhook/send-message
    add_to_list: /webhook/shopping-list
    web_search: /webhook/web-search
    set_reminder: /webhook/set-reminder
  timeout: 10
```

## Example Use Cases

| Voice Command | Tool Called | n8n Action |
|---|---|---|
| "Turn off the living room lights" | `control_smart_home` | → Home Assistant API |
| "What's on my calendar tomorrow?" | `query_calendar` | → Google Calendar API |
| "Send a message to Mom saying I'll be late" | `send_message` | → Telegram/SMS |
| "Add milk to my shopping list" | `add_to_list` | → Notion/Todoist |
| "Remind me to call the dentist at 3pm" | `set_reminder` | → Calendar event/notification |

## Creating Custom Workflows

Any n8n workflow can be triggered by the voice assistant as long as it:
1. Starts with a **Webhook** trigger node (POST method)
2. Accepts JSON body with the tool's parameters
3. Returns a JSON response with a `result` field

Example webhook response format:
```json
{
  "result": "Done! I've turned off the living room lights."
}
```
