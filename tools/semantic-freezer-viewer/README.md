# Standalone adaptive-freezer viewer

On Windows, double-click `open-viewer.cmd`, or run:

```powershell
npm.cmd run viewer:semantic-freezer
```

The viewer opens at:

```text
http://127.0.0.1:5186/tools/semantic-freezer-viewer/index.html
```

The page is standalone from the main application. It embeds only the v4
freezer renderer and exposes independent width, depth, and height controls,
camera orbit, presets, auto-fit, scale locking, and live procedural counts.

The Render pass selector exposes the evidence package used for locked-view
paintovers: raw geometry, part ID, face normal, linear depth, and anchor ID.

For the clearest fixed-size test, turn **Auto-fit** off before changing one
axis. The object may leave the frame at large values; this is intentional and
keeps the world-to-screen scale constant.
