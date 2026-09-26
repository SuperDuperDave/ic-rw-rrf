#!/usr/bin/env python3
"""Reuse bounded acquisition with the Cycle18 plan and public-only HTTP receipts."""
from pathlib import Path
import acquire_cycle17_inputs as base
from public_cycle17_receipts import public_value

ROOT = Path(__file__).resolve().parents[2]
base.__doc__ = __doc__
base.PLAN = ROOT / '_sessions/cycles/2026-09-25-cycle18-input-plan.json'
_base_write = base.write
_base_verify = base.verify_frozen
REQUIRED = (
    '_sessions/tools/acquire_cycle18_inputs.py',
    '_sessions/tools/acquire_cycle17_inputs.py',
    '_sessions/tools/public_cycle17_receipts.py',
    '_sessions/cycles/2026-09-25-cycle18-protocol.md',
    '_sessions/cycles/2026-09-25-cycle18-input-plan.json',
)


def verify(frozen):
    if not set(REQUIRED) <= set(frozen):
        raise ValueError('Cycle18 acquisition source/contract identity missing')
    _base_verify(frozen)


def write(path, value):
    _base_write(path, public_value(value))


base.verify_frozen = verify
base.write = write

if __name__ == '__main__':
    base.main()
