#!/usr/bin/env python3
"""Score cycle06 using preserved custody checks and its own exact loss model."""
import argparse
import score_cycle05_coordinator as driver
from evaluation import cycle06_noisy_lineage as experiment


def score():
    previous_base, previous_experiment = driver.BASE, driver.packets
    try:
        driver.BASE = driver.ROOT / 'results/cycle06-2026-09-10'
        driver.packets = experiment
        driver.score()
    finally:
        driver.BASE, driver.packets = previous_base, previous_experiment


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--score', action='store_true', required=True,
                        help='Score frozen observations offline; no provider calls')
    parser.parse_args()
    score()
