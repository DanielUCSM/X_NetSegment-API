import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv


def main():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    port = int(os.getenv("PORT", "8000"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT debe estar entre 1 y 65535.")
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=port,
        log_level=os.getenv("LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
