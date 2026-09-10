# Krafts Meetings — Contact Management Schema

SQLite schema backing the business-card → contact → AI email flow.

Apply with:

```
sqlite3 krafts.db < schema/contact_management.sql
```

Requires SQLite >= 3.38 (`unixepoch()`) and FTS5. All timestamps are
Unix epoch seconds (INTEGER). All `*_data` / `metadata` columns are JSON
text guarded by `json_valid()`.

## Architecture

```
ChatGPT / Mobile App
        │
        ▼
Business Card Image
        │
        ▼
Vision + Extraction
        │
        ▼
Contact Confirmation
        │
        ▼
   ┌───────────────┐
   │    SQLite     │
   │ Contacts      │
   │ Companies     │
   │ Interactions  │
   │ Templates     │
   │ Email Drafts  │
   │ Settings      │
   └───────┬───────┘
           │
           ▼
    AI Email Engine
           │
           ▼
    Gmail / Outlook
```

## Relationship lifecycle

`contact_relationships.relationship_stage` moves through:

`new_contact` → `met` → `conversation` → `follow_up_required` →
`meeting_scheduled` → `opportunity` → `customer_partner` → `dormant`

`relationship_status` (active / inactive / dormant / closed) is tracked
separately so a relationship can be paused at any stage.

## Tables

| table | purpose |
|---|---|
| `users`, `user_profiles` | account + sender context used when AI writes emails |
| `organizations` | companies extracted from cards or entered manually |
| `contacts` | the core record; extraction confidence + uncertain fields retained |
| `business_card_captures` | original image, extraction status and history |
| `contact_interactions` | meetings, calls, emails, events, notes |
| `contact_relationships` | lifecycle stage, priority, next action |
| `tags`, `contact_tags` | user-defined labels |
| `email_objectives`, `email_templates` | AI email intent + reusable copy (7 system objectives seeded) |
| `generated_emails` | drafts through to sent |
| `app_settings` | per-user defaults and confirmation gates |
| `audit_logs` | entity change trail |
| `contacts_fts` | FTS5 search over name, title, email, phone, company, industry, notes |

FTS is kept in sync by triggers on `contacts` (insert/update/delete) and
on `organizations` rename, which refreshes the denormalised `company_name`.

## Notes / open items

- Data isolation is per `user_id`; queries must filter on it — the schema
  does not enforce a tenant boundary.
- `contacts.email` is intentionally not unique: business cards produce
  duplicates, so de-duplication is an application-layer decision.
- Contact deletion is soft (`status = 'deleted'`) — hard deletes cascade
  to interactions and relationships.
