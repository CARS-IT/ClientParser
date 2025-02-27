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

from clientparser import ClientParser


def main() -> None:
    """Main entry point for the Client Parser application."""
    # Create the client parser instance and run the application
    client_parser = ClientParser()
    client_parser.run()


if __name__ == "__main__":
    main()
