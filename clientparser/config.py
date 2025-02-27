#!/usr/bin/env python3
# ----------------------------------------------------------------------------------
# Project: ClientParser
# File: clientparser/config.py
# ----------------------------------------------------------------------------------
# Purpose:
# This is the main entry point for the Client Parser application.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (C) 2025 GSECARS, The University of Chicago, USA
# Copyright (C) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv
from pathlib import Path
from typing import List

__all__ = ["Config"]

# Load environment variables from .env file
load_dotenv()

# Find the .env file in the root directory
env_path = Path(__file__).resolve().parent.parent / ".env"


@dataclass
class Config:
    """A class that includes the configuration settings for the client parser."""

    _scopes: List[str] = field(init=False, compare=False, repr=False)
    _dhcp_server: str = field(init=False, compare=False, repr=False)
    _database_uri: str = field(init=False, compare=False, repr=False)

    def __post_init__(self) -> None:
        self._scopes = (os.getenv("SCOPES").replace("[", "").replace("]", "").replace(" ", "").split(","))
        self._dhcp_server = os.getenv("DHCP_SERVER")
        self._database_uri = os.getenv("DATABASE_URI")

    @property
    def scopes(self) -> List[str]:
        return self._scopes

    @property
    def dhcp_server(self) -> str:
        return self._dhcp_server

    @property
    def database_uri(self) -> str:
        return self._database_uri
