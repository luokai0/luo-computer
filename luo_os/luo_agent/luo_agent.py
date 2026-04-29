#!/usr/bin/env python3
"""
Luo Agent — Entry Point
Autonomous AI agent for Luo OS powered by LUOKAI native inference.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from core.config import LuoConfig

def main():
    config = LuoConfig()

    if "--daemon" in sys.argv:
        from core.daemon import LuoDaemon
        LuoDaemon(config).start()

    elif "--tui" in sys.argv or "--rich" in sys.argv:
        from ui.tui import run_tui
        run_tui(config)

    elif "--basic" in sys.argv:
        from ui.terminal import LuoTerminal
        LuoTerminal(config).run()

    else:
        # try Textual TUI first, fall back to basic
        try:
            import textual
            from ui.tui import run_tui
            run_tui(config)
        except ImportError:
            from ui.terminal import LuoTerminal
            LuoTerminal(config).run()

if __name__ == "__main__":
    main()
