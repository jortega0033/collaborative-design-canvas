"""Command line entry: python -m design_canvas --data-dir <path> --port <port>"""

import argparse
import sys

from .server import CanvasServer
from .storage import Storage, StorageError


def _port(text):
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError("port must be an integer")
    if not 0 <= value <= 65535:
        raise argparse.ArgumentTypeError("port must be between 0 and 65535")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(prog="design_canvas")
    parser.add_argument("--data-dir", required=True, help="directory for the database")
    parser.add_argument("--port", required=True, type=_port,
                        help="TCP port on 127.0.0.1 (0 picks a free port)")
    args = parser.parse_args(argv)  # argparse exits with code 2 on bad usage

    try:
        storage = Storage(args.data_dir)
    except StorageError as exc:
        print("error: %s" % " ".join(str(exc).split()), file=sys.stderr)
        return 2
    try:
        server = CanvasServer(storage, args.port)
    except OSError as exc:
        storage.close()
        print("error: cannot listen on port %d: %s" % (args.port, exc.strerror or exc),
              file=sys.stderr)
        return 2

    print("Serving on http://127.0.0.1:%d/" % server.port, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()  # closes the socket and joins handler threads
        storage.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
