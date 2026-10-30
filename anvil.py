#!/usr/bin/env python3
"""
Anvil - Honest Professional Visibility Tool

A desktop app for introverts who build things but struggle to talk about themselves.
Generates CVs, cover letters, and project articles that are honest and evidence-based.

Usage:
    python anvil.py              # Launch GUI
    python anvil.py --cli        # CLI mode
    python anvil.py cv           # Generate CV (CLI)
    python anvil.py cover        # Generate cover letter (CLI)
    python anvil.py article      # Generate article (CLI)
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def main():
    """Main entry point."""
    
    args = sys.argv[1:]
    
    # CLI mode
    if args and args[0] == "--cli":
        from cli import main as cli_main
        cli_main()
        return
    
    # Direct commands
    if args:
        command = args[0]
        if command == "cv":
            from cli import generate_cv
            generate_cv()
            return
        elif command == "cover":
            from cli import generate_cover_letter
            generate_cover_letter()
            return
        elif command == "article":
            from cli import generate_article
            generate_article()
            return
        elif command == "check":
            from cli import check_profile
            check_profile()
            return
    
    # Default: launch GUI
    try:
        from ui import run
        run()
    except ImportError as e:
        print(f"GUI not available: {e}")
        print("Install flet: pip install flet")
        print("Or run with --cli for the command-line interface")
        sys.exit(1)

if __name__ == "__main__":
    main()
