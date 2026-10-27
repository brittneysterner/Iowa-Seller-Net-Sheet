# Installing Seller Net Sheet on your Mac

This takes about 10 minutes the first time. You need an internet connection only for the first start.

## Step 1 — Download the app

1. Go to the project page on GitHub (`brittneysterner/iowa-seller-net-sheet`) and sign in.
2. Pick the branch that has the latest version (ask Claude which one).
3. Click the green **Code** button, then **Download ZIP**.
4. Open your **Downloads** folder and double-click the ZIP file. A folder appears.
5. Rename the folder **Seller Net Sheet App** and move it into your **home folder** (the house icon with your
   name in Finder's sidebar). **Don't put it in Documents or Desktop if those sync to iCloud.** On its first start,
   the app downloads many small support files, and iCloud would try to upload them all.

## Step 2 — Start it the first time

1. Open the **Seller Net Sheet App** folder.
2. **Right-click** (or Control-click) **Start Net Sheet.command** and choose **Open**.
3. If your Mac says the file is from an "unidentified developer," click **Open**. You only have to
   do this once. (If there's no Open button, go to **System Settings → Privacy & Security**,
   scroll down, and click **Open Anyway**.)
4. A Terminal window (white or black text window) opens. The first time, it downloads what the app
   needs, which takes a few minutes. Then your web browser opens to the app.

**Keep the Terminal window open while you use the app.** When you're done, close the Terminal window.

## Every time after that

Double-click **Start Net Sheet.command**. The browser opens in a few seconds.

You can also drag **Start Net Sheet.command** to your Dock (next to the Trash) for one-click starting.

## If something goes wrong

- **"Permission denied" or nothing happens:** copy the exact message (or take a screenshot) and send it to Claude.
- **The browser didn't open:** open Safari or Chrome and go to `http://127.0.0.1:8765`
- **"Address already in use":** the app is already running in another Terminal window. Use that one, or close it and start again.

## Your data

Net sheets are saved in **Documents → Seller Net Sheets**. If your Documents folder syncs to iCloud,
or you use Time Machine, they are backed up automatically. If iCloud says your storage is full, new files are
saved on your Mac but **not** backed up until you free up space. Deleting or replacing the app folder does
**not** delete your net sheets.
