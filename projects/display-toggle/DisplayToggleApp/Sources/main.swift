import Cocoa
import SwiftUI

// MARK: - Display Manager

class DisplayManager: ObservableObject {
    @Published var externalDisplayConnected = false
    @Published var externalDisplayEnabled = true
    @Published var statusMessage = "Ready"
    
    private let stateFile = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent(".display-toggle-state")
    
    init() {
        refreshStatus()
    }
    
    func refreshStatus() {
        let (_, external) = getDisplayIds()
        externalDisplayConnected = external != nil
        
        if let ext = external {
            // Check if it's enabled by seeing if it has a resolution
            let output = runDisplayPlacer(["list"])
            externalDisplayEnabled = output.contains(ext) && output.contains("Resolution:")
        }
    }
    
    func getDisplayIds() -> (internal: String?, external: String?) {
        let output = runDisplayPlacer(["list"])
        let lines = output.components(separatedBy: "\n")
        
        var internalId: String?
        var externalId: String?
        var currentId: String?
        
        for line in lines {
            if line.contains("Persistent screen id:") {
                currentId = line.components(separatedBy: ": ").last?.trimmingCharacters(in: .whitespaces)
            }
            if line.contains("Type: MacBook built in") {
                internalId = currentId
            }
            if line.contains("Type: external") {
                externalId = currentId
            }
        }
        
        return (internalId, externalId)
    }
    
    func toggleExternal() {
        let (_, external) = getDisplayIds()
        
        if let extId = external {
            // External is connected and visible - disable it
            disableExternal(id: extId)
        } else if FileManager.default.fileExists(atPath: stateFile.path) {
            // External not visible but we have saved state - try to enable
            enableExternal()
        } else {
            statusMessage = "No external display found"
        }
        
        refreshStatus()
    }
    
    func disableExternal(id: String) {
        // Save current config
        let config = runDisplayPlacer(["list"])
        if let configLine = config.components(separatedBy: "\n").first(where: { $0.contains("displayplacer") }) {
            let saveData = "\(configLine)\n\(id)"
            try? saveData.write(to: stateFile, atomically: true, encoding: .utf8)
        }
        
        // Disable the display
        let result = runDisplayPlacer(["id:\(id) enabled:false"])
        statusMessage = result.isEmpty ? "External display disabled" : result
    }
    
    func enableExternal() {
        guard let savedData = try? String(contentsOf: stateFile, encoding: .utf8) else {
            statusMessage = "No saved state"
            return
        }
        
        let lines = savedData.components(separatedBy: "\n")
        guard lines.count >= 2 else {
            statusMessage = "Invalid state file"
            return
        }
        
        let extId = lines[1].trimmingCharacters(in: .whitespacesAndNewlines)
        
        // Re-enable
        _ = runDisplayPlacer(["id:\(extId) enabled:true"])
        
        // Restore config if possible
        if lines[0].contains("displayplacer") {
            _ = runDisplayPlacer(Array(lines[0].dropFirst(13).components(separatedBy: " ")))
        }
        
        statusMessage = "External display enabled"
    }
    
    private func runDisplayPlacer(_ args: [String]) -> String {
        let task = Process()
        let pipe = Pipe()
        
        task.executableURL = URL(fileURLWithPath: "/opt/homebrew/bin/displayplacer")
        task.arguments = args
        task.standardOutput = pipe
        task.standardError = pipe
        
        do {
            try task.run()
            task.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            return String(data: data, encoding: .utf8) ?? ""
        } catch {
            // Try /usr/local/bin for Intel Macs
            task.executableURL = URL(fileURLWithPath: "/usr/local/bin/displayplacer")
            do {
                try task.run()
                task.waitUntilExit()
                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                return String(data: data, encoding: .utf8) ?? ""
            } catch {
                return "Error: displayplacer not found"
            }
        }
    }
}

// MARK: - App Delegate

class AppDelegate: NSObject, NSApplicationDelegate {
    var statusItem: NSStatusItem!
    var displayManager = DisplayManager()
    var popover: NSPopover!
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Hide from dock
        NSApp.setActivationPolicy(.accessory)
        
        // Create status bar item
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        
        if let button = statusItem.button {
            updateIcon()
            button.action = #selector(togglePopover)
            button.sendAction(on: [.leftMouseUp, .rightMouseUp])
        }
        
        // Create popover
        popover = NSPopover()
        popover.contentSize = NSSize(width: 280, height: 180)
        popover.behavior = .transient
        popover.contentViewController = NSHostingController(
            rootView: MenuView(displayManager: displayManager, updateIcon: updateIcon)
        )
        
        // Refresh periodically
        Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { [weak self] _ in
            self?.displayManager.refreshStatus()
            self?.updateIcon()
        }
    }
    
    func updateIcon() {
        if let button = statusItem?.button {
            if displayManager.externalDisplayConnected && displayManager.externalDisplayEnabled {
                button.image = NSImage(systemSymbolName: "display.2", accessibilityDescription: "External On")
            } else if displayManager.externalDisplayConnected {
                button.image = NSImage(systemSymbolName: "display", accessibilityDescription: "External Off")
            } else {
                button.image = NSImage(systemSymbolName: "display.trianglebadge.exclamationmark", accessibilityDescription: "No External")
            }
        }
    }
    
    @objc func togglePopover() {
        if let button = statusItem.button {
            if popover.isShown {
                popover.performClose(nil)
            } else {
                popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
            }
        }
    }
}

// MARK: - SwiftUI Menu View

struct MenuView: View {
    @ObservedObject var displayManager: DisplayManager
    var updateIcon: () -> Void
    
    var body: some View {
        VStack(spacing: 16) {
            // Header
            HStack {
                Image(systemName: "display.2")
                    .font(.title2)
                Text("Display Toggle")
                    .font(.headline)
            }
            .padding(.top, 8)
            
            Divider()
            
            // Status
            HStack {
                Circle()
                    .fill(displayManager.externalDisplayConnected ? 
                          (displayManager.externalDisplayEnabled ? Color.green : Color.orange) : 
                          Color.red)
                    .frame(width: 10, height: 10)
                
                Text(statusText)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                Spacer()
            }
            
            // Toggle Button
            Button(action: {
                displayManager.toggleExternal()
                updateIcon()
            }) {
                HStack {
                    Image(systemName: displayManager.externalDisplayEnabled ? 
                          "display.trianglebadge.exclamationmark" : "display.2")
                    Text(displayManager.externalDisplayEnabled ? 
                         "Disconnect External" : "Reconnect External")
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 8)
            }
            .buttonStyle(.borderedProminent)
            .disabled(!displayManager.externalDisplayConnected && !hasState)
            
            Divider()
            
            // Quit
            Button("Quit") {
                NSApp.terminate(nil)
            }
            .buttonStyle(.plain)
            .foregroundColor(.secondary)
            .font(.caption)
            
            Spacer()
        }
        .padding()
        .frame(width: 280, height: 180)
    }
    
    var statusText: String {
        if !displayManager.externalDisplayConnected {
            return hasState ? "External disconnected (can reconnect)" : "No external display"
        }
        return displayManager.externalDisplayEnabled ? "External display active" : "External display disabled"
    }
    
    var hasState: Bool {
        FileManager.default.fileExists(atPath: 
            FileManager.default.homeDirectoryForCurrentUser
                .appendingPathComponent(".display-toggle-state").path)
    }
}

// MARK: - Main

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
