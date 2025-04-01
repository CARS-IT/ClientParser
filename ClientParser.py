#!/usr/bin/env python3
# ----------------------------------------------------------------------------------
# Project: ClientParser
# File: ClientParser.py
# ----------------------------------------------------------------------------------
# Purpose:
# This is the main entry point for the Client Parser application.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (C) 2025 GSECARS, The University of Chicago, USA
# Copyright (C) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------

import argparse
from clientparser import ClientParser


def main() -> None:
    """Main entry point for the Client Parser application."""
    # Parse the command line arguments
    parser = argparse.ArgumentParser(description="Client Parser")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose mode")
    parser.add_argument("-i", "--interval", type=int, default=0, help="Set the interval in seconds. If the value is 0, the application will run once and exit")
    args = parser.parse_args()

    # Create the client parser instance
    client_parser = ClientParser()

    # Run the client parser with the specified arguments
    client_parser.run(verbose=args.verbose, interval=args.interval)


if __name__ == "__main__":
    main()
