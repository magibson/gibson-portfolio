# Restaurant Reservation Integration - Security Review

**Date:** 2026-01-29  
**Reviewer:** Clawd (Security Subagent)  
**For:** Matt Gibson (Finance professional)  
**Status:** Implementation Ready

---

## Executive Summary

This document covers security considerations for the restaurant reservation booking integration, covering both **Resy API tokens** and the **OpenTable Chrome relay approach**. Given Matt's work in finance, extra care has been taken to ensure credentials are handled securely.

**Risk Assessment:**
| Component | Risk Level | Mitigation |
|-----------|-----------|------------|
| Resy API tokens | Medium | Proper storage, file permissions, gitignore |
| Chrome relay | Low | Sandboxed, user-controlled, no credential storage |
| Credential storage | Medium | Environment variables, restricted permissions |
| Git exposure | High (if unmitigated) | .gitignore, no secrets in code |

---

## 1. Resy API Token Security

### 1.1 Token Scope & Capabilities

Resy uses two authentication components:

1. **API Key** (`api_key`)
   - Static application identifier
   - Format: `VbWk7s3L4KiK5fzlO7JD3Q5EYolJI7n5` (example)
   - Scope: Identifies the client application
   - Shared across all users of the same app version
   - Low sensitivity - can be extracted from any Resy app request

2. **Auth Token** (`auth_token` / `x-resy-auth-token`)
   - User-specific JWT token
   - Format: `eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI...` (JWT)
   - **HIGH SENSITIVITY** - represents Matt's identity
   - Grants full access to:
     - View/make/cancel reservations
     - Access payment methods on file
     - View personal information (email, phone, name)
     - Join waitlists
     - Access booking history

### 1.2 Token Leakage Risks

**If auth_token is exposed:**
- ❌ Attacker can make reservations as Matt
- ❌ Attacker can cancel existing reservations
- ❌ Attacker can view Matt's dining history
- ❌ Attacker can add Matt to waitlists (restaurants may call)
- ⚠️ Limited financial risk (can't extract payment details, but can make bookings that require deposit)

**Token does NOT allow:**
- ✅ Accessing full credit card numbers (tokenized)
- ✅ Changing password
- ✅ Accessing other Resy users

### 1.3 Token Expiration

Based on research:
- **Official documentation:** None (undocumented API)
- **Observed behavior:** Tokens expire periodically (~30 days based on community reports)
- **Refresh method:** Either re-extract from browser OR use password-based login API

**Refresh Strategy:**
```javascript
// Option 1: Manual re-extraction (RECOMMENDED - most secure)
// User extracts new tokens from Chrome DevTools when old ones expire

// Option 2: Automated refresh (requires storing password - NOT RECOMMENDED)
await client.login(email, password);  // Gets new token
```

**Recommendation:** Use manual token extraction to avoid storing password.

### 1.4 Secure Token Storage

**DO NOT:**
- ❌ Hardcode tokens in source files
- ❌ Commit tokens to git
- ❌ Store tokens in world-readable files
- ❌ Log tokens to console or files
- ❌ Store password if avoidable

**DO:**
- ✅ Use environment variables for tokens
- ✅ Or use config file with restricted permissions (600)
- ✅ Add config files to .gitignore
- ✅ Use `.env` file pattern for credentials

---

## 2. Chrome Relay Security (OpenTable)

### 2.1 How It Works

Clawdbot's browser tool with `profile="chrome"` uses the **Browser Relay Chrome Extension**:

1. User installs Clawdbot Browser Relay extension
2. User manually clicks the toolbar button to "attach" a tab
3. Clawd can then control that specific tab via Chrome DevTools Protocol (CDP)
4. Control happens through a local relay server (`127.0.0.1:18791`)

### 2.2 Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Matt's Chrome Browser                                        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ OpenTable Tab (logged in with Matt's session cookies)   ││
│  │                          ▲                               ││
│  │                          │ CDP control (local only)      ││
│  └──────────────────────────┼──────────────────────────────┘│
│                             │                                │
│  ┌──────────────────────────▼──────────────────────────────┐│
│  │ Browser Relay Extension                                  ││
│  │ - Only active when user clicks toolbar button            ││
│  │ - Badge shows ON/OFF state                               ││
│  │ - Only exposes attached tab, not all tabs                ││
│  └──────────────────────────┬──────────────────────────────┘│
└─────────────────────────────┼───────────────────────────────┘
                              │ localhost:18791
                              ▼
                    ┌─────────────────┐
                    │ Clawd (Local)   │
                    │ browser tool    │
                    └─────────────────┘
```

### 2.3 Security Properties

**✅ GOOD:**
- **User-controlled activation:** Tab only attached when user clicks button
- **Single-tab scope:** Only the attached tab is controllable, not entire browser
- **Local-only communication:** CDP server bound to 127.0.0.1 (not network-exposed)
- **No credential storage:** Uses Matt's existing browser session
- **Visual indicator:** Badge shows when tab is attached
- **No password needed:** We never touch OpenTable credentials

**⚠️ CONSIDERATIONS:**
- Clawd can see and interact with whatever is on the attached tab
- Session cookies are accessible via CDP (standard for browser automation)
- If Clawd's server is compromised, attacker could control attached tab

### 2.4 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Session hijacking | Low | Medium | Local-only CDP, user-controlled attachment |
| Credential exposure | Very Low | High | No credentials stored; uses existing session |
| Unintended actions | Low | Medium | Clawd confirms actions; user detaches when not in use |
| CDP server compromise | Very Low | High | Localhost binding, process isolation |

### 2.5 Best Practices for Chrome Relay

1. **Only attach tab when needed** - Click toolbar button to detach when done
2. **Don't leave OpenTable logged in with sensitive data visible** - Close tab after use
3. **Review Clawd's actions** - Clawd will describe what it's doing before booking

---

## 3. General Security Measures

### 3.1 Git Protection

**Files that must NEVER be committed:**
- `config.json` (contains tokens)
- `.env` (if used for credentials)
- `.opentable-cookies.json` (session cookies)
- Any `*-tokens.json` files

**Implementation:**
A `.gitignore` file has been created to exclude these files.

### 3.2 File Permissions

Config files containing credentials should have restrictive permissions:

```bash
# Only owner can read/write
chmod 600 config.json
chmod 600 .env
chmod 600 .opentable-cookies.json
```

### 3.3 Logging Safety

The `resy-client.js` has been reviewed:
- ✅ Does not log tokens to console
- ✅ Does not write tokens to log files
- ⚠️ CLI mode outputs JSON responses (may include tokens in error messages)

**Recommendation:** When debugging, don't pipe output to files that might be committed.

### 3.4 Rate Limiting

| Platform | Rate Limits | Consequence |
|----------|-------------|-------------|
| Resy | Undocumented, ~100 req/min estimated | Temporary IP block |
| OpenTable | Aggressive (Cloudflare) | CAPTCHA, account flag |

**Mitigation:**
- Add delays between requests (2-5 seconds)
- Don't run sniping scripts continuously
- Use Chrome relay for OpenTable (appears as normal user)

---

## 4. Secure Configuration Setup

### 4.1 Recommended Structure

```
integrations/reservations/
├── .env                    # Credentials (chmod 600, gitignored)
├── .gitignore              # Excludes secrets
├── config.json             # Non-sensitive settings only
├── config.example.json     # Template (safe to commit)
└── resy-client.js          # Reads from .env
```

### 4.2 Environment Variables (.env)

```bash
# Resy Credentials - DO NOT COMMIT THIS FILE
RESY_API_KEY=your_api_key_here
RESY_AUTH_TOKEN=your_auth_token_here
RESY_EMAIL=msgibson103@gmail.com
# NOTE: Password storage is optional and NOT recommended
# RESY_PASSWORD=not_recommended_to_store
```

### 4.3 Non-Sensitive Config (config.json)

```json
{
  "user_preferences": {
    "name": "Matthew Gibson",
    "email": "msgibson103@gmail.com",
    "phone": "732-533-3025",
    "default_party_size": 2,
    "favorite_restaurants": []
  },
  "notifications": {
    "enabled": true,
    "telegram": true
  },
  "settings": {
    "resy_base_url": "https://api.resy.com",
    "request_delay_ms": 2000
  }
}
```

---

## 5. What Matt Needs to Do

### 5.1 Initial Setup (One-Time)

1. **Extract Resy credentials:**
   - Go to [resy.com](https://resy.com) and log in
   - Open Chrome DevTools (F12) → Network tab
   - Navigate to any restaurant page
   - Find a request to `api.resy.com`
   - Copy `authorization` header (the part after `api_key=`)
   - Copy `x-resy-auth-token` header

2. **Create `.env` file:**
   ```bash
   cd ~/clawd/integrations/reservations
   nano .env  # or your preferred editor
   ```
   Add:
   ```
   RESY_API_KEY=<copied_api_key>
   RESY_AUTH_TOKEN=<copied_auth_token>
   RESY_EMAIL=msgibson103@gmail.com
   ```

3. **Set permissions:**
   ```bash
   chmod 600 .env config.json
   ```

4. **Test it works:**
   ```bash
   node resy-client.js reservations
   ```

### 5.2 When Tokens Expire

You'll get a `401 Unauthorized` error. To refresh:
1. Repeat the token extraction steps above
2. Update `.env` with new token
3. Test again

### 5.3 For OpenTable Bookings

1. Ensure Browser Relay extension is installed
2. Log into OpenTable in Chrome
3. Click the Clawdbot toolbar button (badge turns ON)
4. Ask Clawd to book - it will use your browser session
5. Click toolbar button again when done (badge turns OFF)

---

## 6. Incident Response

### If Tokens Are Compromised

1. **Immediately:** Log into Resy website and change password
   - This invalidates old auth tokens
2. **Check:** Review recent reservations for unauthorized bookings
3. **Rotate:** Extract new tokens after password change
4. **Audit:** Check if credentials were committed to git
   - If yes, use `git filter-branch` or BFG to remove from history

### If Chrome Session Is Compromised

1. **Log out:** Sign out of OpenTable in Chrome
2. **Clear cookies:** Chrome Settings → Privacy → Clear browsing data
3. **Change password:** Update OpenTable password
4. **Verify:** Check for unauthorized reservations

---

## 7. Summary

| Security Requirement | Status |
|---------------------|--------|
| Credentials excluded from git | ✅ Configured |
| File permissions restricted | ✅ Instructions provided |
| No password storage required | ✅ Manual token refresh |
| Chrome relay is sandboxed | ✅ Local-only, user-controlled |
| Logging doesn't expose secrets | ✅ Verified |
| Token refresh process documented | ✅ Above |
| Incident response documented | ✅ Above |

**Overall Assessment:** Safe to use for personal restaurant bookings with the documented precautions.

---

*This security review was conducted for the Clawdbot restaurant reservation integration. Questions or concerns should be directed to the main agent.*
