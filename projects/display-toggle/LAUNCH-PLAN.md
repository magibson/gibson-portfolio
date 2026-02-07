# Display Toggle - Launch Plan 🚀

**Goal:** Release a free, open-source Mac app that lets you disconnect/reconnect external displays without unplugging the cable. A free alternative to BetterDisplay Pro's $22 feature.

---

## Why This Could Pop

- Solves a real annoyance (getting up to unplug monitor)
- BetterDisplay charges $22 for this one feature
- Clean, simple, does one thing well
- Good "first open source project" energy

---

## Phase 1: GitHub Release (This Weekend?)

### Tasks
- [ ] Create GitHub repo: `mattgibson/display-toggle` (or similar)
- [ ] Clean up code (Jarvis will prep this)
- [ ] Write proper README with:
  - [ ] What it does (with GIF demo)
  - [ ] One-command install
  - [ ] Screenshots of menu bar
  - [ ] Credits to displayplacer
- [ ] Add MIT license
- [ ] Create first release tag (v1.0.0)

### Nice to Have
- [ ] App icon (simple monitor icon with power symbol?)
- [ ] Record a 10-second GIF demo

---

## Phase 2: Easy Install

### Option A: Unsigned App (Free)
- Build release .app bundle
- Zip it, attach to GitHub release
- Users right-click → Open to bypass Gatekeeper
- Instructions in README

### Option B: Signed App ($99/year)
- Requires Apple Developer Program membership
- App is trusted, no security warnings
- Can notarize for extra trust
- **Decision:** Skip for now unless it takes off

### Option C: Homebrew Cask
- Submit to homebrew-cask repo
- Users install with: `brew install --cask display-toggle`
- Requires Option A or B first

---

## Phase 3: Marketing (Optional)

- [ ] Post on Reddit: r/macapps, r/macOS
- [ ] Hacker News "Show HN"
- [ ] Product Hunt launch
- [ ] Tweet about it

---

## Name Ideas

- **Display Toggle** (current, simple)
- **Disconnect** 
- **MonitorOff**
- **DisplaySwitch**
- **Unplug**

---

## Tech Stack

- Swift + SwiftUI (menu bar app)
- displayplacer CLI (open source dependency)
- ~150 lines of code total

---

## Files Ready

- `display-toggle.sh` - Shell script version (working)
- `DisplayToggleApp/` - SwiftUI menu bar app (working)
- `README.md` - Basic docs (needs polish)

---

## Notes

- Matt's first open source release! 🎉
- Keep it simple - one feature, done well
- Could be a nice portfolio piece for tech credibility

---

*Saved: Feb 4, 2026*
*Status: Planning - Weekend Project*
