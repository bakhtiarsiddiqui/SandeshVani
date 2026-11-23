# Campaign Brief Schema

Input schema for `POST /api/v1/ai/campaigns/generate`.

## `CampaignBrief` Specification

| Field | Type | Required | Constraints | Description |
|---|---|---|---|---|
| `channel` | string | Yes | `sms`, `whatsapp`, `email`, `push` | Delivery channel (enforces length limits) |
| `language` | string | Yes | `hi`, `en`, `mr`, `pa`, `ta`, `te`, `bn`, `gu`, `kn` | Target language code (BCP-47) |
| `tone` | string | No | Default: `professional`, Max: 50 chars | Copywriting tone (e.g. `friendly`, `urgent`) |
| `key_facts` | object | Yes | Valid `KeyFacts` object | Verbatim facts required in draft |
| `organization_id`| UUID | No | UUIDv4 | Optional tenant owning the generated draft |

### `KeyFacts` Object

| Field | Type | Required | Constraints | Description |
|---|---|---|---|---|
| `event` | string | Yes | 1–200 characters | Name of event, program, or scheme |
| `date` | string | Yes | 1–50 characters | Date, schedule, or deadline |
| `venue` | string | Yes | 1–200 characters | Physical location or virtual URL |
| `cost` | string | Yes | 1–50 characters | Price or "Free" |
| `contact` | string | Yes | 1–100 characters | Helpdesk number, SMS code, or email |

### Channel Limits

| Channel | Max Characters | Validation Strategy |
|---|---|---|
| `sms` | 160 | Warns if `char_count > 160` |
| `whatsapp` | 1,024 | Warns if `char_count > 1024` |
| `push` | 256 | Warns if `char_count > 256` |
| `email` | 10,000 | Warns if `char_count > 10000` |
