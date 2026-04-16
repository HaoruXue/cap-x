from __future__ import annotations

import argparse
import pickle
from pathlib import Path

from openpi_client.websocket_client_policy import WebsocketClientPolicy


def main() -> None:
    parser = argparse.ArgumentParser(description="Relay OpenPI inference through the OpenPI env client.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--payload", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = pickle.loads(Path(args.payload).read_bytes())
    client = WebsocketClientPolicy(host=args.host, port=args.port)
    result = client.infer(payload)
    Path(args.output).write_bytes(pickle.dumps(result))


if __name__ == "__main__":
    main()
