#!/usr/bin/env python3
"""Reuse the frozen acquisition gates, retaining only public HTTP headers."""
import acquire_cycle17_inputs as original
from public_cycle17_receipts import public_value


if __name__ == "__main__":
    write_original = original.write

    def write_public(path, value):
        write_original(path, public_value(value))

    original.write = write_public
    original.main()
