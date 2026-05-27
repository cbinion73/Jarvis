#!/usr/bin/env python3
"""
JARVIS Menu Bar App
A persistent macOS menu bar app that shows JARVIS server status
and provides quick access to the JARVIS web interface.
"""

import os
import subprocess
import threading
import urllib.request
import urllib.error

import rumps

JARVIS_URL = "http://127.0.0.1:8787"
STATUS_URL = f"{JARVIS_URL}/api/status"
LOG_PATH = "/Users/chris/Desktop/CODE/JARVIS/data/logs/jarvis-dashboard.stdout.log"
ICON_PATH = "/Users/chris/Desktop/CODE/JARVIS/assets/jarvis_menubar_icon.png"
LAUNCHD_SERVICE = f"gui/{os.getuid()}/com.chris.jarvis.dashboard"

# How often (seconds) to poll server status
POLL_INTERVAL = 30


class JarvisMenuBar(rumps.App):
    def __init__(self):
        # Use icon if it exists, otherwise fall back to text title
        if os.path.exists(ICON_PATH):
            super().__init__("", icon=ICON_PATH, template=True, quit_button=None)
        else:
            super().__init__("J·", quit_button=None)

        self._offline_count = 0
        self._last_ok = None  # None = unknown, True = running, False = offline

        # Build menu items
        self.server_status = rumps.MenuItem("● Server: Checking…")
        self.server_status.set_callback(None)  # non-clickable status label

        self.menu = [
            rumps.MenuItem("Open JARVIS", callback=self.open_jarvis),
            None,  # separator
            self.server_status,
            rumps.MenuItem("↺ Restart Server", callback=self.restart_server),
            None,  # separator
            rumps.MenuItem("📋 View Logs", callback=self.view_logs),
            None,  # separator
            rumps.MenuItem("Quit Menu Bar App", callback=self.quit_app),
        ]

        # Kick off an immediate background status check without blocking __init__
        threading.Thread(target=self._poll_status, daemon=True).start()

    # ------------------------------------------------------------------ #
    #  Menu actions                                                        #
    # ------------------------------------------------------------------ #

    def open_jarvis(self, _):
        subprocess.run(["open", JARVIS_URL])

    def restart_server(self, _):
        try:
            subprocess.run(
                ["launchctl", "kickstart", "-k", LAUNCHD_SERVICE],
                capture_output=True,
                timeout=10,
            )
            rumps.notification(
                "JARVIS",
                "Restarting server…",
                "Give it ~10 seconds then check status.",
            )
        except Exception as exc:
            rumps.notification("JARVIS", "Restart failed", str(exc))
        # Re-poll after 12 s to reflect new state
        threading.Timer(12, self._poll_status).start()

    def view_logs(self, _):
        if os.path.exists(LOG_PATH):
            subprocess.run(["open", "-a", "Console", LOG_PATH])
        else:
            rumps.notification("JARVIS", "Log not found", LOG_PATH)

    def quit_app(self, _):
        rumps.quit_application()

    # ------------------------------------------------------------------ #
    #  Status polling                                                      #
    # ------------------------------------------------------------------ #

    @rumps.timer(POLL_INTERVAL)
    def poll_status_timer(self, _):
        """Called by rumps every POLL_INTERVAL seconds on a background thread."""
        self._poll_status()

    def _poll_status(self):
        """Check /api/status and update menu label + title accordingly."""
        ok = self._check_server()

        if ok:
            self._offline_count = 0
            self.server_status.title = "● Server: Running"
            # Restore normal title (no alarm)
            if not os.path.exists(ICON_PATH):
                self.title = "J·"
        else:
            self._offline_count += 1
            self.server_status.title = "○ Server: Offline"
            # Signal alarm in text title after 2 consecutive failures
            if not os.path.exists(ICON_PATH) and self._offline_count >= 2:
                self.title = "J·⚠"

        self._last_ok = ok

    def _check_server(self) -> bool:
        """Return True if the server responds with HTTP 200."""
        try:
            with urllib.request.urlopen(STATUS_URL, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False


if __name__ == "__main__":
    JarvisMenuBar().run()
