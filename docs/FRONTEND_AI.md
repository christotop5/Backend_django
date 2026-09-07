# VORA — Frontend AI Integration Guide

Base URL: **`https://vora-ujbv.onrender.com/api/v1`**

Configure backend `.env`:
```env
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=openai/gpt-4o-mini
```

---

## Endpoints overview

| Priority | Endpoint | Auth | Purpose |
|----------|----------|------|---------|
| 1 | `POST /ai/parse-ride` | Bearer | NL → structured ride + estimate |
| 2 | `POST /ai/chat` | Optional | VORA Guide chatbot |
| 3 | `POST /ai/resolve-destination` | — | Nickname → carrefour |
| 4 | `POST /ai/driver-briefing` | Bearer (driver) | Daily corridor tips |
| 5 | `POST /ai/classify-sos` | Bearer | SOS text classification |

---

## 1. Natural-language ride booking

**User prompt examples (send as `text`):**
- *"Je suis au Mokolo, je vais à Bastos, 1 place, MTN MoMo"*
- *"De Warda au centre, partagé, cash"*
- *"Deïdo vers Akwa, 2 places, Orange Money"*

```ts
const API = 'https://vora-ujbv.onrender.com/api/v1';

async function parseRide(text: string, city?: string) {
  const res = await fetch(`${API}/ai/parse-ride`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ text, city: city ?? 'Yaoundé' }),
  });
  const json = await res.json();
  if (!json.success) throw new Error(json.error?.message);
  return json.data;
}
```

**Response (excerpt):**
```json
{
  "success": true,
  "data": {
    "pickup_carrefour_id": 4,
    "pickup_name": "Marché Mokolo",
    "destination_carrefour_id": 2,
    "destination_name": "Rond-point Bastos",
    "ride_type": "shared",
    "seats_count": 1,
    "payment_method": "momo",
    "confidence": 0.92,
    "explanation_fr": "Mokolo vers Bastos, paiement MoMo.",
    "estimate": { "estimated_fare_fcfa": 400 },
    "request_payload": { "...": "ready for POST /rides/request" }
  }
}
```

**Then book:**
```ts
async function bookFromAI(text: string) {
  const parsed = await parseRide(text);
  if (parsed.confidence < 0.6) {
    // show confirmation UI with pickup/destination pickers
    return parsed;
  }
  const ride = await fetch(`${API}/rides/request`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(parsed.request_payload),
  });
  return ride.json();
}
```

---

## 2. VORA Guide chatbot

Works **without login** (optional JWT for personalized answers).

**Suggested starter prompts (UI chips):**
- *"Comment payer avec MTN MoMo ?"*
- *"Différence shared et direct ?"*
- *"C'est quoi un carrefour VORA ?"*
- *"Comment devenir chauffeur ?"*

```ts
type ChatMessage = { role: 'user' | 'assistant'; content: string };

async function voraChat(messages: ChatMessage[], city?: string) {
  const res = await fetch(`${API}/ai/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, city }),
  });
  const json = await res.json();
  return json.data as ChatMessage;
}

// Usage
const history: ChatMessage[] = [
  { role: 'user', content: 'C\'est combien de Mokolo à Bastos ?' },
];
const reply = await voraChat(history);
history.push(reply);
```

---

## 3. Destination nickname resolver

Use in pickup/drop autocomplete when user types informal names.

**Prompt examples (`text`):**
- *"mokolo"*, *"wanda"*, *"deido"*, *"campus"*, *"je go akwa"*

```ts
async function resolvePlace(text: string, role: 'pickup' | 'destination', city?: string) {
  const res = await fetch(`${API}/ai/resolve-destination`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, role, city }),
  });
  return (await res.json()).data;
}
```

**Response:**
```json
{
  "carrefour_id": 4,
  "carrefour_name": "Marché Mokolo",
  "city": "Yaoundé",
  "confidence": 0.95,
  "alternatives": []
}
```

---

## 4. Driver corridor briefing

**Driver app — show on cockpit open or "Briefing" button.**

```ts
async function getDriverBriefing(city?: string) {
  const res = await fetch(`${API}/ai/driver-briefing`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${driverAccessToken}`,
    },
    body: JSON.stringify({ city }),
  });
  return (await res.json()).data;
}
```

**UI:** display `headline_fr`, `tips[]`, `hot_carrefours[]`, button *"Activer corridor Y1"* → `POST /driver/corridor`.

---

## 5. SOS classification

Call **before** or **with** `POST /safety/sos`:

```ts
async function classifySOS(text: string, location: { lat: number; lng: number }) {
  const res = await fetch(`${API}/ai/classify-sos`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      text,
      emergency_type: 'police_or_danger',
      location,
    }),
  });
  return (await res.json()).data;
}
```

Show `passenger_message_fr` and `recommended_action_fr` while SOS is sent.

---

## Error codes

| Code | HTTP | Action |
|------|------|--------|
| `AI_NOT_CONFIGURED` | 503 | Backend missing `OPENROUTER_API_KEY` |
| `AI_REQUEST_FAILED` | 502 | Retry or fallback to manual form |
| `AI_PARSE_FAILED` | 422 | Ask user to rephrase or pick carrefours manually |
| `FORBIDDEN` | 403 | Driver-only endpoint |

---

## Recommended UX flow (passenger app)

```
[Text input: "Describe your ride"]
        ↓
POST /ai/parse-ride
        ↓
Show summary card (pickup, dest, fare, confidence)
        ↓
User confirms → POST /rides/request with request_payload
```

## Recommended UX flow (chat widget)

```
Floating "VORA Guide" button
        ↓
POST /ai/chat with message history
        ↓
If user asks to book → switch to parse-ride flow
```

---

Swagger: `/api/v1/docs/` → tag **AI**
