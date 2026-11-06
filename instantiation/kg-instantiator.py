#!/usr/bin/env python3
"""KG Instantiator: create or refresh a pilot or participant JSON snapshot."""
from scripts.generate_kg import main

if __name__ == "__main__":
    main(refresh=True)
