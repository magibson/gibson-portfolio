# Display Toggle - Feature Expansion Report 🚀

**Research Date:** Feb 4, 2026  
**Goal:** Identify features that would differentiate Display Toggle from existing apps and solve real pain points

---

## The Competitive Landscape

| App | Price | Key Features |
|-----|-------|--------------|
| **BetterDisplay** | $22 | Soft-disconnect, DDC, XDR brightness, virtual screens |
| **SwitchResX** | $16 | Resolution switching, display sets, app-based switching |
| **Displays (Jibapps)** | $10 | Quick resolution, arrangement, keyboard shortcuts |
| **MonitorControl** | Free | Brightness/volume control only |
| **displayplacer** | Free (CLI) | Resolution, arrangement - command line only |

**Gap:** No free, simple app that solves the #1 complaint.

---

## The #1 Pain Point: Display Arrangement Amnesia 🧠

**The Problem (from Reddit/forums - VERY common):**
> "It's 2022/2023/2024/2025, and my MacBook Pro STILL can't remember the arrangement of multiple external monitors."

Every time users:
- Wake from sleep
- Reboot
- Reconnect monitors
- Unplug/replug dock

...macOS randomly shuffles which monitor is "left" and "right". Users have to manually re-drag displays in System Settings constantly.

**Why it happens:** macOS identifies monitors by connection order, not by serial number. If two identical monitors wake at slightly different times, they swap.

**The Opportunity:** A FREE app that **reliably remembers and restores display arrangements** would be a killer feature no one else does well (even paid apps struggle).

---

## Feature Expansion Ideas (Ranked by Impact)

### 🥇 Tier 1: High Impact, Solves Real Pain

#### 1. **Display Profiles / Layouts**
Save and restore complete display setups:
- Which displays are on/off
- Resolution for each
- Arrangement (left/right/above/below)
- Primary display
- Name each profile ("Work", "Gaming", "Presentation")

**Switch profiles via:**
- Menu bar dropdown
- Keyboard shortcut
- Automatic triggers

**Why it's different:** Existing tools do this poorly or it's buried in complex UIs. Make it dead simple.

#### 2. **Auto-Restore After Sleep/Wake**
Automatically detect when displays have swapped positions and fix them without user intervention.
- Watch for wake events
- Compare current arrangement to saved
- Auto-correct if wrong

**This alone would make the app go viral** - it's the most complained-about macOS display issue.

#### 3. **Quick Toggle Per-Display**
Show all connected displays in menu bar dropdown, let user toggle each one individually (not just "the external").

Great for setups with 2-3 monitors where you want to turn off one specific screen.

---

### 🥈 Tier 2: Nice to Have, Differentiators

#### 4. **App-Based Auto-Switching**
When specific apps launch, automatically:
- Enable/disable certain displays
- Switch to a profile
- Change resolution

Example: Launch Final Cut → enable reference monitor, switch to 4K. Close → revert.

SwitchResX does this but costs $16. Make it free.

#### 5. **Location/Network-Based Profiles**
Detect WiFi network or connected dock and auto-apply profile:
- At office → "Work" profile
- At home → "Home" profile
- On the go (no external) → internal only

#### 6. **Keyboard Shortcuts for Everything**
- Toggle external: ⌘⇧D
- Switch to Profile 1: ⌘⌥1
- Cycle through profiles: ⌘⌥→

Make them user-configurable.

#### 7. **Display Info Panel**
Show useful info about each display:
- Resolution & refresh rate
- Connection type (HDMI, USB-C, DisplayPort)
- Serial number
- DDC capability

Helps users troubleshoot.

---

### 🥉 Tier 3: Advanced / Future

#### 8. **DDC Brightness/Volume Control**
Control external monitor brightness and volume from the menu bar (like MonitorControl).

Not core to Display Toggle but would make it more useful as an all-in-one tool.

#### 9. **PIP/Virtual Display**
Create a picture-in-picture window of a display, or virtual displays for streaming/recording.

Complex - probably out of scope for v1.

#### 10. **Multi-Mac Sync**
Sync profiles across multiple Macs via iCloud or config file.

Nice for users with MacBook + iMac.

---

## Recommended MVP Feature Set

For the first public release, focus on:

### Core (What we have)
- ✅ Toggle external display on/off
- ✅ Menu bar app
- ✅ Remember state for reconnection

### Add for Launch
- 🔲 **Display Profiles** (save/restore named layouts)
- 🔲 **Auto-restore after wake** (the killer feature)
- 🔲 **Per-display toggle** (if multiple externals)
- 🔲 **Keyboard shortcuts**

### Post-Launch
- 🔲 App-based auto-switching
- 🔲 Location/WiFi-based profiles
- 🔲 DDC brightness control

---

## Naming & Positioning

**Current name:** Display Toggle  
**Tagline ideas:**
- "Your displays, your way. For free."
- "The display manager macOS should have built in."
- "Stop fighting your monitors."

**Positioning:** The free, simple alternative to BetterDisplay/SwitchResX for the features most people actually need.

---

## Marketing Angles

1. **"Save $22"** - BetterDisplay's disconnect feature is paid; ours is free
2. **"Fix macOS's biggest bug"** - Display arrangement amnesia solved
3. **"Open source"** - Transparent, community-driven
4. **"One app, one job"** - Does display management without bloat

---

## Technical Notes

- **displayplacer** handles the heavy lifting (resolution, arrangement)
- Need to add arrangement detection + comparison logic
- Profile storage: simple JSON in ~/Library/Application Support/DisplayToggle/
- Wake detection: Use NSWorkspace notifications for screen wake/sleep

---

## Next Steps

1. Decide on MVP feature set with Matt
2. Build display profiles + auto-restore
3. Polish UI
4. Create GitHub repo + README with GIF demos
5. Release v1.0
6. Post to Reddit r/macapps, r/macOS, Hacker News
7. Iterate based on feedback

---

*Report generated by Jarvis - Feb 4, 2026*
