import threading

import uvicorn

from dashboard.server import app
from main import main_loop


def run_main():
    # loop หลักของบอท
    main_loop()


def run_dashboard():
    # uvicorn รัน FastAPI dashboard
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    # รัน main บน thread แยก
    t = threading.Thread(target=run_main, daemon=True)
    t.start()

    # process หลักให้รัน dashboard (กด Ctrl+C จะหยุดทั้งชุด)
    run_dashboard()
