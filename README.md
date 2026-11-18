# PixelStudy 🎮

A school reminder and Pomodoro desktop app made with **Python**.
This is the simplified version for a Data Structures and Algorithms (DSA) finals project.

## Run the app on Windows

1. Install Python (3.10 or newer).
2. Open this `PixelStudy` folder in File Explorer.
3. Click the address bar, type `cmd`, and press Enter.
4. Install the one graphics library:

   ```bat
   py -m pip install -r requirements.txt
   ```

5. Run the app:

   ```bat
   py main.py
   ```

## What the buttons do

- **START** opens the menu. **EXIT** closes the app.
- **REMINDERS** shows four Eisenhower Matrix sections.
- **+** or **+ ADD TASK** lets you enter a task, subject, date, time, and priorities.
- Each task has **EDIT** and **DELETE** buttons. There is **no right-click menu**.
- To **move a task to another section**, click EDIT and change its **Urgent** / **Important** checkboxes.
- Click the little task checkbox to mark it done.
- **UNDO** restores the last task change (using a stack).
- **POMODORO** starts with 25 minutes. Breaks are automatic: 5 minutes after rounds 1–3, longer after round 4.
- **BACK** returns to the previous menu. The timer pauses when you leave its screen.

Data saves automatically to `%APPDATA%\PixelStudy\tasks.json` on Windows.
Reminders only pop up when the app is open.

## Build the `.exe`

Double-click `build_windows.bat` on a Windows PC with Python installed.
It installs the build dependencies and creates `dist\PixelStudy.exe`.

## Which code should I study?

1. **`main.py`**: starts the app.
2. **`pixelstudy/core.py`**: the DSA lesson part. Start here.
3. **`pixelstudy/timer.py`**: Pomodoro countdown and short/long breaks.
4. **`pixelstudy/ui.py`**: draws the windows, pictures, and buttons. It is longer because of all the pixel-art layout code.
5. **`assets/`**: the backgrounds, animation, logo, icons and menu buttons. These are images, not code.

Read **`DEFENSE_GUIDE.md`** for a very short explanation you can use in class.

## Upload to GitHub

Create a repository named `PixelStudy`, then upload the **contents of this folder**. Do not upload the `dist/`, `build/`, `__pycache__/`, or `tasks.json` files if they appear later. The `.gitignore` file already excludes temporary files.

**Art note:** Some image files came from user-provided references. Make sure you are allowed to redistribute them publicly before pushing the images to a public GitHub repository.
