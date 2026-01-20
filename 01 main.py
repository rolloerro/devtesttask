#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Usage:
    python3 main.py --rows 1000000 --csv_file calls.csv
"""

from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta
from typing import TypedDict, Optional, List, Dict

import pandas as pd
import numpy as np


# ===== Константы =====

CAMPAIGNS: list[int] = [1000, 2000, 3000, 4000, 5000, 9000]
AGENTS: list[str] = [f"agent{i:04d}" for i in range(1, 1001)]
STATUSES: list[str] = ["CREDIT", "SALE", "DNC", "NI", "BUSY"]
SALE_STATUSES: set[str] = {"CREDIT", "SALE"}


# ===== Типы данных =====

class WorkBlock(TypedDict):
    start: int
    end: int
    campaign: int


class CallRecord(TypedDict):
    CALLTIME: str
    AGENT: Optional[str]
    CAMPAIGN: int
    STATUS: Optional[str]
    AMOUNT: Optional[int | str]


Schedule = Dict[str, Dict[str, List[WorkBlock]]]


# ===== Генерация расписания =====

def gen_schedule(agents: list[str], days: list[str]) -> Schedule:
    schedule: Schedule = {}

    for agent in agents:
        schedule[agent] = {}

        for day in days:
            work_blocks: list[int] = random.choice([[8], [4, 4], [2, 2, 2, 2]])
            blocks: list[WorkBlock] = []

            start_hour: int = 9 if random.random() < 0.5 else 21 - sum(work_blocks)

            for block_len in work_blocks:
                start = start_hour
                end = start + block_len

                blocks.append({
                    "start": 0 if start == 9 else start,
                    "end": 24 if end == 21 else end,
                    "campaign": random.choice(CAMPAIGNS),
                })

                start_hour += block_len

            schedule[agent][day] = blocks

    return schedule


def get_agents(
    schedule: Schedule,
    campaign: int,
    day: str,
    hour: int
) -> list[str]:
    agents: list[str] = []

    for agent, days in schedule.items():
        for block in days.get(day, []):
            if (
                block["campaign"] == campaign
                and block["start"] <= hour < block["end"]
            ):
                agents.append(agent)

    return agents


# ===== Генерация звонков =====

def get_time(day: str) -> datetime:
    day_obj = datetime.strptime(day, "%Y-%m-%d")

    start_time = datetime.combine(day_obj, datetime.strptime("08:50", "%H:%M").time())
    end_time = datetime.combine(day_obj, datetime.strptime("21:10", "%H:%M").time())

    delta_seconds = int((end_time - start_time).total_seconds())
    return start_time + timedelta(seconds=random.randint(0, delta_seconds))


def gen_status(campaign: int) -> Optional[str]:
    if random.random() < 0.005:
        return None

    sale_weight: float = 10.0 if campaign in CAMPAIGNS[-2:] else 4.0
    other_weight: float = (100.0 - sale_weight) / (len(STATUSES) - len(SALE_STATUSES))

    weights: list[float] = (
        [sale_weight / len(SALE_STATUSES)] * len(SALE_STATUSES)
        + [other_weight] * (len(STATUSES) - len(SALE_STATUSES))
    )

    return random.choices(STATUSES, weights=weights)[0]


def gen_amount(status: Optional[str]) -> Optional[int | str]:
    if status in SALE_STATUSES:
        if random.random() < 0.005:
            return None
        return random.randrange(0, 105, 5)
    return ""


def gen_calls(
    day: str,
    rows: int,
    schedule: Schedule
) -> pd.DataFrame:
    calls: list[CallRecord] = []

    for _ in range(rows):
        call_time = get_time(day)
        campaign = (
            random.choice(CAMPAIGNS[:-2])
            if random.random() < 0.7
            else random.choice(CAMPAIGNS[-2:])
        )

        agents = get_agents(schedule, campaign, day, call_time.hour)

        if agents:
            agent = random.choice(agents)
            status = gen_status(campaign)
            amount = gen_amount(status)
        else:
            agent = None
            status = "NA"
            amount = None

        calls.append({
            "CALLTIME": call_time.strftime("%Y-%m-%d %H:%M:%S"),
            "AGENT": agent,
            "CAMPAIGN": campaign,
            "STATUS": status,
            "AMOUNT": amount,
        })

    return pd.DataFrame(calls)


# ===== Точка входа =====

def main(rows: int, csv_file: str) -> None:
    print(f"Generating {rows} calls → {csv_file}")

    today = datetime.today()
    start_date = today - timedelta(days=today.weekday() + 7)

    days: list[str] = [
        (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(5)
    ]

    schedule = gen_schedule(AGENTS, days)

    calls_by_day = np.full(5, rows // 5)
    calls_by_day[: rows % 5] += 1

    frames: list[pd.DataFrame] = [
        gen_calls(day, int(count), schedule)
        for day, count in zip(days, calls_by_day)
    ]

    result = pd.concat(frames, ignore_index=True)
    result.to_csv(csv_file, index=False)

    print(f"Generated {len(result)} rows")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate call records CSV")
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--csv_file", type=str, default="calls.csv")

    args = parser.parse_args()
    main(rows=args.rows, csv_file=args.csv_file)
