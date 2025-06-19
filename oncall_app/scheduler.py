import random
import calendar
import datetime as _dt
from typing import List, Dict, Set
from .holiday_utils import is_holiday

SHIFT_JP = {"WE_DAY": "休日 日直", "WE_NIGHT": "休日 宿直", "WD_NIGHT": "平日 宿直"}
REQUIRED = {"WE_DAY": 1, "WE_NIGHT": 1, "WD_NIGHT": 2}


def generate_shift_slots(year: int, month: int):
    cal = calendar.Calendar(firstweekday=6)  # Sunday first
    slots = []
    for d in cal.itermonthdates(year, month):
        if d.month != month:
            continue
        if d.weekday() >= 5 or is_holiday(d):  # 土日祝
            slots += [(d, "WE_DAY"), (d, "WE_NIGHT")]
        else:  # 平日
            slots.append((d, "WD_NIGHT"))
    return slots


def ok_gap(seq, lo=5, hi=8):
    seq = sorted(seq)
    return all(lo <= (seq[i + 1] - seq[i]).days <= hi for i in range(len(seq) - 1))


def make_schedule(
    year: int,
    month: int,
    doctors: List[str],
    unavailable: Dict[str, Set[tuple]],
    attempts=30000,
    seed=42,
    gap_lo=5,
    gap_hi=8,
):
    random.seed(seed)
    for d in doctors:
        unavailable.setdefault(d, set())

    slots = generate_shift_slots(year, month)
    stock = {tp: [d for d, t in slots if t == tp] for tp in REQUIRED}

    # 枠数チェック
    if any(len(stock[tp]) < REQUIRED[tp] * len(doctors) for tp in REQUIRED):
        raise RuntimeError("この月はシフト枠が不足しています。")

    def try_once():
        pool = {k: v[:] for k, v in stock.items()}
        for v in pool.values():
            random.shuffle(v)
        assign = {}
        for doc in random.sample(doctors, len(doctors)):
            picks = []
            # ── 4 枠の割当順をランダムに ──
            typ_list = ["WE_DAY", "WE_NIGHT", "WD_NIGHT", "WD_NIGHT"]
            random.shuffle(typ_list)
            for typ in typ_list:
                cand = [
                    d
                    for d in pool[typ]
                    if (d, typ) not in unavailable[doc] and ok_gap(picks + [d], gap_lo, gap_hi)
                ]
                if not cand:
                    return None
                ch = random.choice(cand)
                picks.append(ch)
                pool[typ].remove(ch)
            assign[doc] = list(zip(picks, typ_list))
        # 成功
        return sorted(
            [
                {"Date": d, "Shift": SHIFT_JP[tp], "Doctor": doc}
                for doc, l in assign.items()
                for d, tp in l
            ],
            key=lambda r: (r["Date"], r["Shift"]),
        )

    for _ in range(attempts):
        res = try_once()
        if res:
            return res
    raise RuntimeError("条件を満たす組み合わせが見つかりませんでした。")