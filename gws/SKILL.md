---
name: gws
description: Interact with Google Workspace (Gmail, Calendar, Drive, Sheets, Docs, Tasks) using the gws CLI. Use when the user wants to send emails, check calendar, manage files, read/write spreadsheets, or automate workspace tasks.
argument-hint: [service] [command] [options]
---

# Google Workspace CLI (gws) Skill

## CLI Binary & Auth Status

- **Binary:** `gws` (installed via npm)
- **Auth check:** `gws auth status`

## Output Formatting

All commands support these output formats:
- `--format json` (default)
- `--format table` (human-readable)
- `--format yaml`
- `--format csv`

## Pagination

- `--page-all` - Stream all results
- `--page-limit N` - Limit pages
- `--page-delay MS` - Delay between requests

---

## Gmail Operations

### Triage Inbox
```bash
gws gmail +triage --format table --max 10
```

### Send Email
```bash
gws gmail +send --to "email@example.com" --subject "Subject" --body "Message"
gws gmail +send --to "email@example.com" --cc "cc@example.com" --bcc "bcc@example.com" --subject "Subject" --body "Message"
```

### Reply to Message
```bash
gws gmail +reply --message-id "MSG_ID" --body "Reply text"
gws gmail +reply-all --message-id "MSG_ID" --body "Reply to all"
```

### Forward Message
```bash
gws gmail +forward --message-id "MSG_ID" --to "forward@example.com"
```

### List Messages
```bash
gws gmail users messages list --params '{"userId": "me", "maxResults": 10}'
gws gmail users messages list --params '{"userId": "me", "labelIds": ["INBOX"], "maxResults": 10}'
```

### Get Message
```bash
gws gmail users messages get --params '{"userId": "me", "id": "MSG_ID"}'
```

---

## Calendar Operations

### Show Agenda
```bash
gws calendar +agenda --format table
gws calendar +agenda --days 7 --format table
```

### Create Event
```bash
gws calendar events insert --params '{"calendarId": "primary"}' --json '{"summary": "Meeting", "start": {"dateTime": "2026-03-18T10:00:00-03:00"}, "end": {"dateTime": "2026-03-18T11:00:00-03:00"}}'
```

### List Calendars
```bash
gws calendar calendarList list --format table
```

### List Events
```bash
gws calendar events list --params '{"calendarId": "primary", "maxResults": 10}'
gws calendar events list --params '{"calendarId": "primary", "timeMin": "2026-03-17T00:00:00Z", "maxResults": 10}'
```

### Get Event Details
```bash
gws calendar events get --params '{"calendarId": "primary", "eventId": "EVENT_ID"}'
```

---

## Drive Operations

### Upload File
```bash
gws drive +upload --file "./report.pdf" --name "Report 2026"
gws drive +upload --file "./report.pdf" --name "Report 2026" --folder "FOLDER_ID"
```

### List Files
```bash
gws drive files list --params '{"pageSize": 10}' --format table
```

### Search Files
```bash
gws drive files list --params '{"q": "name contains '\''report'\''", "pageSize": 10}'
gws drive files list --params '{"q": "mimeType = '\''application/vnd.google-apps.spreadsheet'\''", "pageSize": 10}'
```

### Download File
```bash
gws drive files get --params '{"fileId": "FILE_ID"}' --output ./downloaded_file.pdf
```

### Export Google Doc/Sheet
```bash
gws drive files export --params '{"fileId": "FILE_ID", "mimeType": "application/pdf"}' --output ./exported.pdf
```

### Share File
```bash
gws drive permissions create --params '{"fileId": "FILE_ID"}' --json '{"role": "reader", "type": "user", "emailAddress": "user@example.com"}'
```

---

## Sheets Operations

### Read Range
```bash
gws sheets +read --spreadsheet "SHEET_ID" --range "SheetName!A1:C10"
```

### Append Row
```bash
gws sheets +append --spreadsheet "SHEET_ID" --range "SheetName!A:C" --values '[["val1", "val2", "val3"]]'
```

### Get Spreadsheet Metadata
```bash
gws sheets spreadsheets get --params '{"spreadsheetId": "SHEET_ID"}'
```

### Batch Update Values
```bash
gws sheets spreadsheets values batchUpdate --params '{"spreadsheetId": "SHEET_ID"}' --json '{"valueInputOption": "RAW", "data": [{"range": "Sheet1!A1", "values": [["Updated"]]}]}'
```

**Note:** Use single quotes around ranges with exclamation marks to prevent shell history expansion.

---

## Docs Operations

### Append Text to Document
```bash
gws docs +write --document-id "DOC_ID" --text "Text to append"
```

### Get Document Content
```bash
gws docs documents get --params '{"documentId": "DOC_ID"}'
```

### Create New Document
```bash
gws docs documents create --json '{"title": "New Document"}'
```

---

## Tasks Operations

### List Task Lists
```bash
gws tasks tasklists list --format table
```

### List Tasks
```bash
gws tasks tasks list --params '{"tasklist": "@default"}' --format table
```

### Create Task
```bash
gws tasks tasks insert --params '{"tasklist": "@default"}' --json '{"title": "New task"}'
gws tasks tasks insert --params '{"tasklist": "@default"}' --json '{"title": "New task", "due": "2026-03-20T00:00:00Z"}'
```

### Update Task
```bash
gws tasks tasks update --params '{"tasklist": "@default", "task": "TASK_ID"}' --json '{"title": "Updated title"}'
```

### Complete Task
```bash
gws tasks tasks update --params '{"tasklist": "@default", "task": "TASK_ID"}' --json '{"status": "completed"}'
```

### Move Task
```bash
gws tasks tasks move --params '{"tasklist": "@default", "task": "TASK_ID", "parent": "PARENT_TASK_ID"}'
```

---

## Workflow Helpers

### Standup Report
Today's meetings + open tasks:
```bash
gws workflow +standup-report --format table
```

### Meeting Prep
Prepare for next meeting:
```bash
gws workflow +meeting-prep --format json
```

### Email to Task
Convert email to task:
```bash
gws workflow +email-to-task --message-id "MSG_ID"
```

### Weekly Digest
Weekly summary:
```bash
gws workflow +weekly-digest --format table
```

---

## Usage Patterns

| User Request | Command |
|--------------|---------|
| "Check my email" / "What's in my inbox?" | `gws gmail +triage` |
| "Send an email to X" | `gws gmail +send` |
| "What's on my calendar?" / "My agenda" | `gws calendar +agenda` |
| "Schedule a meeting" | `gws calendar +insert` |
| "List my Drive files" | `gws drive files list` |
| "Upload this file" | `gws drive +upload` |
| "Read spreadsheet X" | `gws sheets +read` |
| "Add row to spreadsheet" | `gws sheets +append` |
| "My tasks" / "Todo list" | `gws tasks tasks list` |
| "Add a task" | `gws tasks tasks insert` |
| "Prepare for my next meeting" | `gws workflow +meeting-prep` |
| "What do I have today?" | `gws workflow +standup-report` |

---

## Notes

- All commands use JSON for --params and --json flags
- Shell history expansion (exclamation mark) in ranges requires single quotes around the range
- Helper commands (prefixed with +) are shortcuts for common operations
- Use --dry-run flag to preview API calls without executing
- Exit codes: 0=success, 1=API error, 2=auth error, 3=validation error
