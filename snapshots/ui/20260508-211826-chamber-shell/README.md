Snapshot: 20260508-211826-chamber-shell

Purpose:
- Preserve the current JARVIS chamber shell, background, and review state.
- Provide a clean restore point if later UI work drifts.

Captured files:
- `voice_ui.py`
- `web.py`
- `Chamber.jpg`
- `holo-review.json`
- `voice.json`
- `locations.json`

Restore:
1. Copy `voice_ui.py` back to `/Users/chris/Desktop/CODE/JARVIS/jarvis/voice_ui.py`
2. Copy `web.py` back to `/Users/chris/Desktop/CODE/JARVIS/jarvis/web.py`
3. Copy `Chamber.jpg` back to `/Users/chris/Desktop/CODE/JARVIS/assets/Chamber.jpg`
4. Copy `holo-review.json` back to `/Users/chris/Desktop/CODE/JARVIS/data/design-review/holo-review.json`
5. Copy `voice.json` back to `/Users/chris/Desktop/CODE/JARVIS/data/settings/voice.json`
6. Copy `locations.json` back to `/Users/chris/Desktop/CODE/JARVIS/data/settings/locations.json`
7. Restart JARVIS on port `8787`

Notes:
- This snapshot preserves the shell code plus the saved visual review state.
- It is intended as a manual restore point, not an automated migration.
