# Tools

## MSE2 Pyxel Visualizer

`mse2_pyxel_visualizer.py` opens Magic Set Editor 2 `.mse-set` files and renders
a generic Pyxel preview of each card. It supports zipped `.mse-set` archives and
extracted directories that contain a `set` file.

Install the viewer dependencies in the repo virtualenv:

```powershell
.venv\Scripts\python.exe -m pip install -r tools\requirements.txt
```

List cards without launching Pyxel:

```powershell
.venv\Scripts\python.exe tools\mse2_pyxel_visualizer.py "C:\Users\arthexis\Desktop\data\sets\NormalMagicSet.mse-set" --list
```

Launch the visualizer:

```powershell
.venv\Scripts\python.exe tools\mse2_pyxel_visualizer.py "C:\Users\arthexis\Desktop\data\sets\NormalMagicSet.mse-set"
```

Use a larger integer-scaled window when screenshots or monitor scaling make the
native pixels look soft:

```powershell
.venv\Scripts\python.exe tools\mse2_pyxel_visualizer.py "C:\Users\arthexis\Desktop\data\sets\NormalMagicSet.mse-set" --display-scale 3
```

Render one card to a PNG without opening the viewer:

```powershell
.venv\Scripts\python.exe tools\mse2_pyxel_visualizer.py "C:\Users\arthexis\Desktop\data\sets\NormalMagicSet.mse-set" --card 6 --render "C:\Users\arthexis\Desktop\leyline.png" --image-scale 2
```

Render every card in a set:

```powershell
.venv\Scripts\python.exe tools\mse2_pyxel_visualizer.py "C:\Users\arthexis\Desktop\data\sets\NormalMagicSet.mse-set" --render-all "C:\Users\arthexis\Desktop\NormalMagicSet-renders"
```

Controls:

- `Left` / `Right`, `A` / `D`, or `K` / `J`: previous or next card
- `Home` / `End`: first or last card
- `S`: save the current card as a PNG
- `Q` or `Esc`: quit

The renderer does not execute MSE stylesheet scripts. It parses the set data and
draws a compact card approximation with title, cost, embedded art, type line,
rules text, flavor text, and footer metadata.
