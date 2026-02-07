# Display Toggle 🖥️

A simple Mac utility to disconnect/reconnect your external display without unplugging the cable.

## Quick Start (Shell Script)

### 1. Install displayplacer

```bash
brew install displayplacer
```

### 2. Make script executable

```bash
chmod +x ~/clawd/projects/display-toggle/display-toggle.sh
```

### 3. Use it

```bash
# Toggle external display on/off
./display-toggle.sh

# Just turn it off
./display-toggle.sh off

# Turn it back on
./display-toggle.sh on

# List connected displays
./display-toggle.sh list
```

### 4. Add keyboard shortcut (optional)

**Option A: Raycast**
1. Open Raycast preferences
2. Extensions → Script Commands → Add
3. Point to `display-toggle.sh`
4. Assign hotkey (e.g., ⌘⇧D)

**Option B: Automator**
1. Open Automator → New → Quick Action
2. Add "Run Shell Script"
3. Paste: `/Users/YOUR_USERNAME/clawd/projects/display-toggle/display-toggle.sh`
4. Save as "Toggle Display"
5. System Preferences → Keyboard → Shortcuts → Services → Assign hotkey

---

## Menu Bar App (Fancier)

A proper macOS menu bar app with:
- Status icon showing display state
- Click to toggle
- Visual feedback

### Build it

```bash
cd ~/clawd/projects/display-toggle/DisplayToggleApp
swift build -c release
```

### Run it

```bash
.build/release/DisplayToggle
```

### Make it start at login

1. Build the release version
2. Copy to Applications: `cp -r .build/release/DisplayToggle /Applications/`
3. System Settings → General → Login Items → Add DisplayToggle

---

## How It Works

Uses `displayplacer`, an open-source CLI tool, to:
1. Save your current display configuration
2. Disable the external display (removes it from macOS)
3. Re-enable it and restore the configuration

The external display goes to sleep when disabled, just like unplugging HDMI.

## Troubleshooting

**"displayplacer not found"**
```bash
brew install displayplacer
```

**Can't re-enable display**
- Try running `./display-toggle.sh on`
- If that fails, unplug and replug the cable (resets the state)

**Wrong display gets toggled**
- Run `./display-toggle.sh list` to see display IDs
- Edit the script if needed for your setup

## Credits

- [displayplacer](https://github.com/jakehilborn/displayplacer) - The underlying CLI tool
- Built as a free alternative to BetterDisplay Pro's $22 soft-disconnect feature
