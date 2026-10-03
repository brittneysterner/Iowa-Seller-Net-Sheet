"""Start the app:  python -m netsheet

Opens your web browser to the app. The app only listens on this computer
(127.0.0.1), so nobody else on your network or the internet can reach it.
"""

import logging
import os
import threading
import webbrowser

from werkzeug.serving import make_server

from .web.app import app

PORT = int(os.environ.get("NETSHEET_PORT", "8765"))


def main():
    url = f"http://127.0.0.1:{PORT}/"
    if os.environ.get("NETSHEET_NO_BROWSER") != "1":
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"\nSeller Net Sheet is running at {url}")
    print("Keep this window open while you use the app. Close it (or press Control-C) to stop.\n")
    logging.getLogger("werkzeug").setLevel(logging.ERROR)  # keep the window quiet
    server = make_server("127.0.0.1", PORT, app, threaded=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    main()
