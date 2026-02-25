# Interface Contract

**РСЃС‚РѕС‡РЅРёРє РїСЂР°РІРґС‹:** `admin-app/src-tauri/src/lib.rs`, `admin-app/src-tauri/src/main.rs`, `admin-app/src/stores/*.js`, `backend/api/*.py`

**Р’РµСЂСЃРёСЏ:** 1.0  
**Р”Р°С‚Р°:** 2026-02-17

## РђСЂС…РёС‚РµРєС‚СѓСЂР° РІР·Р°РёРјРѕРґРµР№СЃС‚РІРёСЏ

```
Svelte 5 Frontend в†ђв†’ Tauri 2.0 (Rust) в†ђв†’ FastAPI Backend
     в†“                    в†“                    в†“
  Stores            Commands          HTTP Endpoints
```

## 1. РўР°Р±Р»РёС†Р° РјР°РїРїРёРЅРіР° РєРѕРјР°РЅРґ

### Authentication & Session

| Svelte Store Action | Tauri Command | Rust HTTP Client | FastAPI Endpoint |
|-------------------|---------------|------------------|------------------|
| `sessionStore.setToken()` | `login` | `api_client::login()` | `POST /api/token` (РїСѓР±Р»РёС‡РЅС‹Р№) |

### Guests Management

| Svelte Store Action | Tauri Command | Rust HTTP Client | FastAPI Endpoint |
|-------------------|---------------|------------------|------------------|
| `guestStore.fetchGuests()` | `get_guests` | `api_client::get_guests()` | `GET /api/guests/` (JWT) |
| `guestStore.createGuest()` | `create_guest` | `api_client::create_guest()` | `POST /api/guests/` (JWT) |
| `guestStore.updateGuest()` | `update_guest` | `api_client::update_guest()` | `PUT /api/guests/{id}` (JWT) |
| `guestStore.bindCardToGuest()` | `bind_card_to_guest` | `api_client::bind_card_to_guest()` | `POST /api/guests/{id}/cards` (JWT) |
| `guestStore.topUpBalance()` | `top_up_balance` | `api_client::top_up_balance()` | `POST /api/guests/{id}/topup` (JWT) |

### Kegs Management

| Svelte Store Action | Tauri Command | Rust HTTP Client | FastAPI Endpoint |
|-------------------|---------------|------------------|------------------|
| `kegStore.fetchKegs()` | `get_kegs` | `api_client::get_kegs()` | `GET /api/kegs/` (JWT) |
| `kegStore.createKeg()` | `create_keg` | `api_client::create_keg()` | `POST /api/kegs/` (JWT) |
| `kegStore.updateKeg()` | `update_keg` | `api_client::update_keg()` | `PUT /api/kegs/{id}` (JWT) |
| `kegStore.deleteKeg()` | `delete_keg` | `api_client::delete_keg()` | `DELETE /api/kegs/{id}` (JWT) |

### Taps Management

| Svelte Store Action | Tauri Command | Rust HTTP Client | FastAPI Endpoint |
|-------------------|---------------|------------------|------------------|
| `tapStore.fetchTaps()` | `get_taps` | `api_client::get_taps()` | `GET /api/taps/` (JWT) |
| `tapStore.assignKegToTap()` | `assign_keg_to_tap` | `api_client::assign_keg_to_tap()` | `PUT /api/taps/{id}/keg` (JWT) |
| `tapStore.unassignKegFromTap()` | `unassign_keg_from_tap` | `api_client::unassign_keg_from_tap()` | `DELETE /api/taps/{id}/keg` (JWT) |
| `tapStore.updateTapStatus()` | `update_tap` | `api_client::update_tap()` | `PUT /api/taps/{id}` (JWT) |

### Beverages Management

| Svelte Store Action | Tauri Command | Rust HTTP Client | FastAPI Endpoint |
|-------------------|---------------|------------------|------------------|
| `beverageStore.fetchBeverages()` | `get_beverages` | `api_client::get_beverages()` | `GET /api/beverages/` (JWT) |
| `beverageStore.createBeverage()` | `create_beverage` | `api_client::create_beverage()` | `POST /api/beverages/` (JWT) |

### System & Monitoring

| Svelte Store Action | Tauri Command | Rust HTTP Client | FastAPI Endpoint |
|-------------------|---------------|------------------|------------------|
| `systemStore.fetchStatus()` | `get_system_status` | `api_client::get_system_status()` | `GET /api/system/status` (JWT) |
| `systemStore.setEmergencyStop()` | `set_emergency_stop` | `api_client::set_emergency_stop()` | `POST /api/system/emergency_stop` (JWT) |
| `pourStore.fetchPours()` | `get_pours` | `api_client::get_pours()` | `GET /api/pours/` (JWT) |

### NFC Operations (Local only)

| Svelte Store Action | Tauri Command | Rust Implementation | FastAPI Endpoint |
|-------------------|---------------|-------------------|------------------|
| `nfcReaderStore.setupListener()` | `list_readers` | `nfc_handler::list_readers_internal()` | вЂ” |
| вЂ” | `read_mifare_block` | `nfc_handler::connect_and_authenticate()` | вЂ” |
| вЂ” | `write_mifare_block` | `nfc_handler::connect_and_authenticate()` | вЂ” |
| вЂ” | `change_sector_keys` | `nfc_handler::connect_and_authenticate()` | вЂ” |

## 2. РЎРѕР±С‹С‚РёСЏ NFC: `card-status-changed`

### РћСЃРЅРѕРІРЅРѕР№ СЃРїРѕСЃРѕР± РїРѕР»СѓС‡РµРЅРёСЏ РґР°РЅРЅС‹С… NFC

**РќР°РїСЂР°РІР»РµРЅРёРµ:** Rust в†’ Svelte  
**РњРµС…Р°РЅРёР·Рј:** Tauri Events  
**Р§Р°СЃС‚РѕС‚Р°:** 500ms polling СЃ РёРґРµРјРїРѕС‚РµРЅС‚РЅРѕР№ РѕС‚РїСЂР°РІРєРѕР№

#### РЎС‚СЂСѓРєС‚СѓСЂР° payload:

```typescript
interface CardStatusPayload {
  uid?: string;      // HEX UID РєР°СЂС‚С‹ РёР»Рё null
  error?: string;    // РћС€РёР±РєР° PC/SC РёР»Рё null
}
```

#### Р›РѕРіРёРєР° РѕР±СЂР°Р±РѕС‚РєРё РІ `nfcReaderStore`:

```javascript
const handleEvent = (payload) => {
  update(currentState => {
    if (payload.error) {
      return { 
        ...currentState, 
        status: 'error', 
        error: payload.error, 
        lastUid: null 
      };
    }
    
    return { 
      ...currentState, 
      status: 'ok', 
      error: null, 
      lastUid: payload.uid || null 
    };
  });
};
```

#### РЎС†РµРЅР°СЂРёРё СЃС‚Р°С‚СѓСЃР°:

| РЎС†РµРЅР°СЂРёР№ | UID | Error | Status | РћРїРёСЃР°РЅРёРµ |
|----------|-----|-------|--------|----------|
| РљР°СЂС‚Р° РЅР° СЂРёРґРµСЂРµ | HEX string | null | 'ok' | РљР°СЂС‚Р° РѕР±РЅР°СЂСѓР¶РµРЅР° Рё РїСЂРѕС‡РёС‚Р°РЅР° |
| Р РёРґРµСЂ РїСѓСЃС‚ | null | null | 'ok' | Р РёРґРµСЂ РґРѕСЃС‚СѓРїРµРЅ, РєР°СЂС‚С‹ РЅРµС‚ |
| РћС€РёР±РєР° PC/SC | null | string | 'error' | РђРїРїР°СЂР°С‚РЅР°СЏ РѕС€РёР±РєР° СЂРёРґРµСЂР° |
| Р РёРґРµСЂ РЅРµ РЅР°Р№РґРµРЅ | null | "РЎС‡РёС‚С‹РІР°С‚РµР»СЊ РЅРµ РЅР°Р№РґРµРЅ" | 'error' | Р РёРґРµСЂ РѕС‚РєР»СЋС‡РµРЅ |

#### РРґРµРјРїРѕС‚РµРЅС‚РЅРѕСЃС‚СЊ:

РЎРѕР±С‹С‚РёРµ РѕС‚РїСЂР°РІР»СЏРµС‚СЃСЏ С‚РѕР»СЊРєРѕ РїСЂРё РёР·РјРµРЅРµРЅРёРё payload. РЎСЂР°РІРЅРµРЅРёРµ РїСЂРѕРёСЃС…РѕРґРёС‚ С‡РµСЂРµР· JSON СЃРµСЂРёР°Р»РёР·Р°С†РёСЋ:

```rust
if current_payload_json != last_payload_json {
    app_handle.emit("card-status-changed", payload.clone())?;
    last_payload_json = current_payload_json;
}
```

## 3. РљР»Р°СЃСЃРёС„РёРєР°С†РёСЏ СЌРЅРґРїРѕРёРЅС‚РѕРІ API

### РџСѓР±Р»РёС‡РЅС‹Рµ СЌРЅРґРїРѕРёРЅС‚С‹ (РґР»СЏ RPi)

| Endpoint | Method | РћРїРёСЃР°РЅРёРµ | РСЃРїРѕР»СЊР·РѕРІР°РЅРёРµ |
|----------|--------|----------|---------------|
| `/api/token` | POST | РђСѓС‚РµРЅС‚РёС„РёРєР°С†РёСЏ | РџРѕР»СѓС‡РµРЅРёРµ JWT С‚РѕРєРµРЅР° |
| `/api/system/status` | GET | РЎС‚Р°С‚СѓСЃ СЌРєСЃС‚СЂРµРЅРЅРѕР№ РѕСЃС‚Р°РЅРѕРІРєРё | РћРїСЂРѕСЃ RPi РєРѕРЅС‚СЂРѕР»Р»РµСЂР°РјРё |
| `/api/guests/{id}` | GET | РџРѕР»СѓС‡РµРЅРёРµ РіРѕСЃС‚СЏ РїРѕ ID | RPi РґР»СЏ РїСЂРѕРІРµСЂРєРё Р±Р°Р»Р°РЅСЃР° |
| `/api/controllers/register` | POST | Р РµРіРёСЃС‚СЂР°С†РёСЏ РєРѕРЅС‚СЂРѕР»Р»РµСЂР° | Check-in RPi РєРѕРЅС‚СЂРѕР»Р»РµСЂРѕРІ |
| `/api/sync/pours` | POST | РЎРёРЅС…СЂРѕРЅРёР·Р°С†РёСЏ РЅР°Р»РёРІРѕРІ | РћС‚РїСЂР°РІРєР° РґР°РЅРЅС‹С… Рѕ РЅР°Р»РёРІР°С… |

**РћСЃРѕР±РµРЅРЅРѕСЃС‚Рё:**
- РќРµ С‚СЂРµР±СѓСЋС‚ JWT Р°СѓС‚РµРЅС‚РёС„РёРєР°С†РёРё
- РћРїС‚РёРјРёР·РёСЂРѕРІР°РЅС‹ РґР»СЏ С‡Р°СЃС‚РѕРіРѕ РѕРїСЂРѕСЃР°
- Р’РѕР·РІСЂР°С‰Р°СЋС‚ РјРёРЅРёРјР°Р»СЊРЅРѕ РЅРµРѕР±С…РѕРґРёРјС‹Рµ РґР°РЅРЅС‹Рµ
- **РўСЂРµР±РѕРІР°РЅРёРµ Р·Р°РіРѕР»РѕРІРєР° `X-Internal-Token`** РґР»СЏ СЌРЅРґРїРѕРёРЅС‚РѕРІ РєРѕРЅС‚СЂРѕР»Р»РµСЂРѕРІ (СЃРј. СЂР°Р·РґРµР» 7)

### Р­РЅРґРїРѕРёРЅС‚С‹ С‚СЂРµР±СѓСЋС‰РёРµ JWT (РґР»СЏ Admin App)

#### Guests API
- `GET /api/guests/` - РЎРїРёСЃРѕРє РіРѕСЃС‚РµР№
- `POST /api/guests/` - РЎРѕР·РґР°РЅРёРµ РіРѕСЃС‚СЏ
- `PUT /api/guests/{id}` - РћР±РЅРѕРІР»РµРЅРёРµ РіРѕСЃС‚СЏ
- `POST /api/guests/{id}/cards` - РџСЂРёРІСЏР·РєР° РєР°СЂС‚С‹
- `POST /api/guests/{id}/topup` - РџРѕРїРѕР»РЅРµРЅРёРµ Р±Р°Р»Р°РЅСЃР°
- `GET /api/guests/{id}/history` - РСЃС‚РѕСЂРёСЏ РѕРїРµСЂР°С†РёР№

#### Kegs API
- `GET /api/kegs/` - РЎРїРёСЃРѕРє РєРµРі
- `POST /api/kegs/` - РЎРѕР·РґР°РЅРёРµ РєРµРіРё
- `PUT /api/kegs/{id}` - РћР±РЅРѕРІР»РµРЅРёРµ РєРµРіРё
- `DELETE /api/kegs/{id}` - РЈРґР°Р»РµРЅРёРµ РєРµРіРё

#### Taps API
- `GET /api/taps/` - РЎРїРёСЃРѕРє РєСЂР°РЅРѕРІ
- `PUT /api/taps/{id}/keg` - РќР°Р·РЅР°С‡РµРЅРёРµ РєРµРіРё
- `DELETE /api/taps/{id}/keg` - РЎРЅСЏС‚РёРµ РєРµРіРё
- `PUT /api/taps/{id}` - РћР±РЅРѕРІР»РµРЅРёРµ РєСЂР°РЅР°

#### Beverages API
- `GET /api/beverages/` - РЎРїРёСЃРѕРє РЅР°РїРёС‚РєРѕРІ
- `POST /api/beverages/` - РЎРѕР·РґР°РЅРёРµ РЅР°РїРёС‚РєР°

#### System API
- `POST /api/system/emergency_stop` - РЈРїСЂР°РІР»РµРЅРёРµ СЌРєСЃС‚СЂРµРЅРЅРѕР№ РѕСЃС‚Р°РЅРѕРІРєРѕР№
- `GET /api/system/states/all` - Р’СЃРµ С„Р»Р°РіРё СЃРёСЃС‚РµРјС‹ (debug)

#### Cards API
- `GET /api/cards/` - РЎРїРёСЃРѕРє РІСЃРµС… РєР°СЂС‚
- `POST /api/cards/` - Р РµРіРёСЃС‚СЂР°С†РёСЏ РєР°СЂС‚С‹
- `PUT /api/cards/{uid}/status` - РР·РјРµРЅРµРЅРёРµ СЃС‚Р°С‚СѓСЃР° РєР°СЂС‚С‹

#### Pours API
- `GET /api/pours/` - РСЃС‚РѕСЂРёСЏ РЅР°Р»РёРІРѕРІ

## 4. РџРѕС‚РѕРєРё РґР°РЅРЅС‹С…

### РђСѓС‚РµРЅС‚РёС„РёРєР°С†РёСЏ:
```
UI в†’ sessionStore в†’ invoke('login') в†’ api_client::login() в†’ POST /api/token
                                            в†“
UI в†ђ sessionStore в†ђ JWT С‚РѕРєРµРЅ в†ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
```

### CRUD РѕРїРµСЂР°С†РёРё:
```
UI в†’ store в†’ invoke('command') в†’ api_client::function() в†’ HTTP endpoint
                                            в†“
UI в†ђ store в†ђ РћР±РЅРѕРІР»РµРЅРЅС‹Рµ РґР°РЅРЅС‹Рµ в†ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
```

### NFC СЃРѕР±С‹С‚РёСЏ:
```
Rust NFC thread в†’ card-status-changed в†’ nfcReaderStore в†’ UI
```

## 5. РћР±СЂР°Р±РѕС‚РєР° РѕС€РёР±РѕРє

### Rust в†’ Svelte:
```rust
#[derive(Debug, Serialize, Clone)]
pub struct AppError { 
    message: String,
}
```

### Svelte в†’ UI:
```javascript
try {
  await store.action();
} catch (error) {
  // error.message РёР»Рё error.toString()
}
```

### HTTP РѕС€РёР±РєРё:
```rust
async fn handle_api_error(response: Response) -> String {
    if let Ok(error_body) = response.json::<ApiErrorDetail>().await {
        error_body.detail
    } else {
        format!("HTTP Error: {}", response.status())
    }
}
```

## 6. РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ

### API Base URL:
```rust
const API_BASE_URL: &str = "http://localhost:8000/api";
```

### JWT С‚РѕРєРµРЅ:
```javascript
// РҐСЂР°РЅРёС‚СЃСЏ РІ localStorage
localStorage.setItem('jwt_token', token);
```

### NFC РѕРїСЂРѕСЃ:
```rust
thread::sleep(Duration::from_millis(500));
```

## 7. РђСѓС‚РµРЅС‚РёС„РёРєР°С†РёСЏ РєРѕРЅС‚СЂРѕР»Р»РµСЂРѕРІ (X-Internal-Token)

### РўСЂРµР±РѕРІР°РЅРёРµ РґР»СЏ СЌРЅРґРїРѕРёРЅС‚РѕРІ РєРѕРЅС‚СЂРѕР»Р»РµСЂРѕРІ

РЎР»РµРґСѓСЋС‰РёРµ РїСѓР±Р»РёС‡РЅС‹Рµ СЌРЅРґРїРѕРёРЅС‚С‹ С‚СЂРµР±СѓСЋС‚ Р·Р°РіРѕР»РѕРІРѕРє `X-Internal-Token` РґР»СЏ Р°СѓС‚РµРЅС‚РёС„РёРєР°С†РёРё RPi РєРѕРЅС‚СЂРѕР»Р»РµСЂРѕРІ:

- `POST /api/controllers/register` - Р РµРіРёСЃС‚СЂР°С†РёСЏ РєРѕРЅС‚СЂРѕР»Р»РµСЂР°
- `POST /api/sync/pours` - РЎРёРЅС…СЂРѕРЅРёР·Р°С†РёСЏ РЅР°Р»РёРІРѕРІ

### Р¤РѕСЂРјР°С‚ Р·Р°РіРѕР»РѕРІРєР°

```http
X-Internal-Token: <secret_token_string>
```

### РњРµС…Р°РЅРёР·Рј РїСЂРѕРІРµСЂРєРё

1. **РЎРµСЂРІРµСЂРЅР°СЏ РІР°Р»РёРґР°С†РёСЏ:** РўРѕРєРµРЅ РїСЂРѕРІРµСЂСЏРµС‚СЃСЏ РЅР° СЃРѕРѕС‚РІРµС‚СЃС‚РІРёРµ РїСЂРµРґРѕРїСЂРµРґРµР»РµРЅРЅРѕРјСѓ Р·РЅР°С‡РµРЅРёСЋ
2. **Р‘РµР·РѕРїР°СЃРЅРѕСЃС‚СЊ:** РўРѕРєРµРЅ С…СЂР°РЅРёС‚СЃСЏ РІ РїРµСЂРµРјРµРЅРЅС‹С… РѕРєСЂСѓР¶РµРЅРёСЏ СЃРµСЂРІРµСЂР°
3. **Р¦РµР»СЊ:** РџСЂРµРґРѕС‚РІСЂР°С‰РµРЅРёРµ РЅРµСЃР°РЅРєС†РёРѕРЅРёСЂРѕРІР°РЅРЅРѕРіРѕ РґРѕСЃС‚СѓРїР° Рє СЌРЅРґРїРѕРёРЅС‚Р°Рј РєРѕРЅС‚СЂРѕР»Р»РµСЂРѕРІ

### РџСЂРёРјРµСЂ Р·Р°РїСЂРѕСЃР°

```http
POST /api/sync/pours
Content-Type: application/json
X-Internal-Token: rpi_controller_secret_2024

{
  "pours": [
    {
      "client_tx_id": "tx_12345",
      "card_uid": "04AB7815CD6B80",
      "tap_id": 1,
      "start_ts": "2026-02-17T12:00:00Z",
      "end_ts": "2026-02-17T12:00:05Z",
      "volume_ml": 500,
      "price_cents": 350,
      "price_per_ml_at_pour": 0.0070
    }
  ]
}
```

### РџРµСЂРµРјРµРЅРЅС‹Рµ РѕРєСЂСѓР¶РµРЅРёСЏ

```bash
# РќР° СЃРµСЂРІРµСЂРµ backend
INTERNAL_CONTROLLER_TOKEN=rpi_controller_secret_2024
```

---

**РџСЂРёРјРµС‡Р°РЅРёРµ:** Р­С‚РѕС‚ РґРѕРєСѓРјРµРЅС‚ СЏРІР»СЏРµС‚СЃСЏ РёСЃС‚РѕС‡РЅРёРєРѕРј РїСЂР°РІРґС‹ РґР»СЏ РІСЃРµС… РІР·Р°РёРјРѕРґРµР№СЃС‚РІРёР№ РјРµР¶РґСѓ РєРѕРјРїРѕРЅРµРЅС‚Р°РјРё СЃРёСЃС‚РµРјС‹. РџСЂРё РёР·РјРµРЅРµРЅРёРё Р°СЂС…РёС‚РµРєС‚СѓСЂС‹ РЅРµРѕР±С…РѕРґРёРјРѕ РѕР±РЅРѕРІР»СЏС‚СЊ РґР°РЅРЅС‹Р№ РєРѕРЅС‚СЂР°РєС‚.

## M4 API Contract Addendum (2026-02-25)

### Updated sync payload
`POST /api/sync/pours` now requires `short_id` for every pour item:
- `client_tx_id` (string)
- `card_uid` (string)
- `tap_id` (int)
- `short_id` (string, 6-8)
- `start_ts` (datetime)
- `end_ts` (datetime)
- `volume_ml` (int)
- `price_cents` (int)

### New manual reconcile endpoint
`POST /api/visits/{visit_id}/reconcile-pour`
Payload:
- `tap_id` (int)
- `short_id` (string, 6-8)
- `volume_ml` (int)
- `amount` (decimal)
- `reason` (required string)
- `comment` (optional string)

Behavior:
- idempotent by `(visit_id, short_id)`;
- first successful call creates reconciled pour and unlocks visit;
- repeated call returns existing reconciled result.

### Audit actions used in M4
- `reconcile_done`
- `late_sync_matched`
- `late_sync_mismatch`
- `sync_conflict`

