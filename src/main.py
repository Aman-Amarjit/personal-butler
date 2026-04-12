"""
JARVIS AI Assistant - Main Entry Point

Initializes and runs the JARVIS system with voice interaction,
AI processing, and slime body UI.
"""

import sys
import argparse
import logging
from pathlib import Path

from src.ui.overlay import create_overlay


def setup_logging(debug: bool = False) -> None:
    """
    Setup logging configuration.

    Args:
        debug: Enable debug logging
    """
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main() -> int:
    """
    Main entry point for JARVIS.

    Returns:
        Exit code
    """
    parser = argparse.ArgumentParser(
        description="JARVIS AI Assistant"
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Run in development mode"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1920,
        help="Overlay width"
    )
    parser.add_argument(
        "--height",
        type=int,
        default=1080,
        help="Overlay height"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(debug=args.debug or args.dev)
    logger = logging.getLogger(__name__)

    logger.info("Starting JARVIS AI Assistant")
    logger.info(f"Development mode: {args.dev}")

    try:
        # Create and show overlay
        overlay = create_overlay(
            width=args.width,
            height=args.height
        )
        overlay.show()

        logger.info("Overlay created and displayed")

        # Run event loop
        import sys
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        return app.exec()

    except Exception as e:
        logger.error(f"Error starting JARVIS: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
