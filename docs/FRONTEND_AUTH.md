# VORA — Frontend Auth Guide (Access + Refresh Tokens)

Base URL: **`https://vora-ujbv.onrender.com/api/v1`**

---

## Token summary

| Token | Lifetime | Storage (frontend) | Usage |
|-------|----------|-------------------|--------|
| **Access token** | 24 h | Memory + `sessionStorage` | `Authorization: Bearer …` on every API call |
| **Refresh token** | 7 days | `localStorage` or secure storage | `POST /auth/refresh` only — never send on normal requests |

Both tokens are returned by:
- `POST /auth/signin`
- `POST /auth/otp/verify`

---

## 1. Login flow

```http
POST /auth/signin
Content-Type: application/json

{
  "email": "marie.ebanda@gmail.com",
  "password": "pass12345"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Connexion réussie.",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "xK9pQ2mN8vL...",
    "token_type": "Bearer",
    "expires_in": 86400,
    "refresh_expires_in": 604800,
    "user": {
      "id": "usr_1",
      "email": "marie.ebanda@gmail.com",
      "name": "Marie Ebanda",
      "role": "passenger",
      "redirect_dashboard": "pickup"
    }
  }
}
```

**Store:**

```ts
interface AuthSession {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;        // Date.now() + expires_in * 1000
  refreshExpiresAt: number; // Date.now() + refresh_expires_in * 1000
  user: {
    id: string;
    email: string;
    name: string;
    role: 'passenger' | 'driver';
    redirect_dashboard: 'pickup' | 'driver-cockpit';
  };
}

function saveSession(data: AuthSession['user'] & typeof response.data) {
  const session: AuthSession = {
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    expiresAt: Date.now() + data.expires_in * 1000,
    refreshExpiresAt: Date.now() + data.refresh_expires_in * 1000,
    user: data.user,
  };
  sessionStorage.setItem('vora_access', session.accessToken);
  localStorage.setItem('vora_refresh', session.refreshToken);
  localStorage.setItem('vora_user', JSON.stringify(session.user));
  return session;
}
```

**Redirect by role:**

```ts
router.replace(
  user.role === 'driver' ? '/driver/cockpit' : '/passenger/pickup'
);
```

---

## 2. Authenticated API calls

```ts
const API = 'https://vora-ujbv.onrender.com/api/v1';

async function apiFetch(path: string, options: RequestInit = {}) {
  const accessToken = sessionStorage.getItem('vora_access');
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...options.headers,
    },
  });

  if (res.status === 401) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      return apiFetch(path, options); // retry once
    }
    clearSession();
    router.replace('/login');
    throw new Error('Session expired');
  }

  return res.json();
}
```

---

## 3. Refresh token (silent renew)

Call **before** access expires, or on **401**:

```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "<stored refresh token>"
}
```

**Response:** same shape as signin — **new access + new refresh**.

> **Important:** refresh tokens **rotate**. After each refresh, replace the stored refresh token. The old one is revoked.

```ts
let refreshPromise: Promise<boolean> | null = null;

async function tryRefreshToken(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refreshToken = localStorage.getItem('vora_refresh');
    if (!refreshToken) return false;

    const res = await fetch(`${API}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) return false;

    const json = await res.json();
    saveSession(json.data);
    return true;
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}
```

**Proactive refresh (optional):** refresh 5 min before expiry:

```ts
setInterval(async () => {
  const expiresAt = Number(sessionStorage.getItem('vora_expires_at') || 0);
  if (expiresAt && Date.now() > expiresAt - 5 * 60 * 1000) {
    await tryRefreshToken();
  }
}, 60_000);
```

---

## 4. Logout

```http
POST /auth/logout
Content-Type: application/json

{
  "refresh_token": "<stored refresh token>"
}
```

```ts
async function logout() {
  const refreshToken = localStorage.getItem('vora_refresh');
  if (refreshToken) {
    await fetch(`${API}/auth/logout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  }
  clearSession();
  router.replace('/login');
}

function clearSession() {
  sessionStorage.removeItem('vora_access');
  localStorage.removeItem('vora_refresh');
  localStorage.removeItem('vora_user');
}
```

> Access token may still work up to 24 h after logout. Clear it locally and redirect to login.

---

## 5. Route guards (role-based)

```tsx
function ProtectedRoute({ roles, children }: { roles?: string[]; children: React.ReactNode }) {
  const user = JSON.parse(localStorage.getItem('vora_user') || 'null');
  const access = sessionStorage.getItem('vora_access');

  if (!access || !user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) {
    return <Navigate to={user.role === 'driver' ? '/driver/cockpit' : '/passenger/pickup'} replace />;
  }
  return <>{children}</>;
}
```

| Route prefix | Allowed `user.role` |
|--------------|---------------------|
| `/passenger/*` | `passenger` |
| `/driver/*` | `driver` |
| `/login`, `/signup` | public |

---

## 6. App bootstrap (page refresh)

```ts
async function bootstrapAuth() {
  const access = sessionStorage.getItem('vora_access');
  const refresh = localStorage.getItem('vora_refresh');

  if (access) {
    try {
      const me = await apiFetch('/auth/me');
      if (me.success) return me.data;
    } catch { /* fall through to refresh */ }
  }

  if (refresh && (await tryRefreshToken())) {
    const me = await apiFetch('/auth/me');
    if (me.success) return me.data;
  }

  clearSession();
  return null;
}
```

---

## 7. Error codes

| Code | HTTP | Action frontend |
|------|------|-----------------|
| `INVALID_CREDENTIALS` | 401 | Show login error |
| `ACCOUNT_NOT_VERIFIED` | 403 | Redirect to OTP screen |
| `INVALID_REFRESH_TOKEN` | 401 | Clear session → login |
| `INVALID_OTP` | 400 | Show OTP error |

---

## 8. Test accounts

| Role | Email | Password |
|------|-------|----------|
| Passager | `marie.ebanda@gmail.com` | `pass12345` |
| Chauffeur | `alain.mvondo@vora.cm` | `pass12345` |
| OTP (signup) | — | `1234` |

---

## Endpoints reference

| Method | Endpoint | Auth |
|--------|----------|------|
| POST | `/auth/signup` | — |
| POST | `/auth/otp/send` | — |
| POST | `/auth/otp/verify` | — → returns tokens |
| POST | `/auth/signin` | — → returns tokens |
| POST | `/auth/refresh` | — (body: refresh_token) |
| POST | `/auth/logout` | — (body: refresh_token) |
| GET | `/auth/me` | Bearer access token |

Swagger: [https://vora-ujbv.onrender.com/api/v1/docs/](https://vora-ujbv.onrender.com/api/v1/docs/)
