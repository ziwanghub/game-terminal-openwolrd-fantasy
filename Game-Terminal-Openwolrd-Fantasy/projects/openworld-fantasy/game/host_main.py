"""Entry: python -m game.host via package __main__ pattern — see game/host.py"""
from game.host import main

if __name__ == "__main__":
    raise SystemExit(main())
