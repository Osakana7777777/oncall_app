import datetime as _dt
import pytest

from oncall_app.scheduler import generate_shift_slots, ok_gap, make_schedule


class TestGenerateShiftSlots:
    def test_all_dates_in_month(self):
        slots = generate_shift_slots(2024, 6)
        dates = {d for d, _ in slots}
        assert all(d.month == 6 for d in dates)

    def test_weekday_only_wd_night(self):
        # 2024-06-03 is a Monday (weekday)
        slots = generate_shift_slots(2024, 6)
        monday = _dt.date(2024, 6, 3)
        monday_slots = [(d, t) for d, t in slots if d == monday]
        assert monday_slots == [(monday, "WD_NIGHT")]

    def test_weekend_has_we_day_and_we_night(self):
        # 2024-06-01 is a Saturday
        slots = generate_shift_slots(2024, 6)
        saturday = _dt.date(2024, 6, 1)
        saturday_slots = {t for d, t in slots if d == saturday}
        assert saturday_slots == {"WE_DAY", "WE_NIGHT"}

    def test_slot_types_are_valid(self):
        slots = generate_shift_slots(2024, 6)
        valid_types = {"WE_DAY", "WE_NIGHT", "WD_NIGHT"}
        assert all(t in valid_types for _, t in slots)


class TestOkGap:
    def test_valid_gap(self):
        dates = [
            _dt.date(2024, 6, 1),
            _dt.date(2024, 6, 7),
            _dt.date(2024, 6, 13),
        ]
        assert ok_gap(dates, lo=5, hi=8) is True

    def test_gap_too_small(self):
        dates = [
            _dt.date(2024, 6, 1),
            _dt.date(2024, 6, 4),  # 3 days — below lo=5
        ]
        assert ok_gap(dates, lo=5, hi=8) is False

    def test_gap_too_large(self):
        dates = [
            _dt.date(2024, 6, 1),
            _dt.date(2024, 6, 12),  # 11 days — above hi=8
        ]
        assert ok_gap(dates, lo=5, hi=8) is False

    def test_single_date_always_ok(self):
        assert ok_gap([_dt.date(2024, 6, 1)], lo=5, hi=8) is True

    def test_empty_list_ok(self):
        assert ok_gap([], lo=5, hi=8) is True

    def test_unsorted_input(self):
        dates = [
            _dt.date(2024, 6, 13),
            _dt.date(2024, 6, 1),
            _dt.date(2024, 6, 7),
        ]
        assert ok_gap(dates, lo=5, hi=8) is True


class TestMakeSchedule:
    def _make(self, year=2024, month=6, doctors=None, unavail=None, gap_lo=5, gap_hi=8):
        if doctors is None:
            doctors = ["医師A", "医師B", "医師C"]
        if unavail is None:
            unavail = {d: set() for d in doctors}
        return make_schedule(year, month, doctors, unavail, gap_lo=gap_lo, gap_hi=gap_hi)

    def test_returns_list_of_dicts(self):
        rows = self._make()
        assert isinstance(rows, list)
        assert all(isinstance(r, dict) for r in rows)

    def test_row_keys(self):
        rows = self._make()
        for r in rows:
            assert set(r.keys()) == {"Date", "Shift", "Doctor"}

    def test_each_doctor_gets_4_shifts(self):
        doctors = ["医師A", "医師B", "医師C"]
        rows = self._make(doctors=doctors)
        from collections import Counter
        counts = Counter(r["Doctor"] for r in rows)
        assert all(counts[d] == 4 for d in doctors)

    def test_shift_types_are_valid(self):
        rows = self._make()
        valid_shifts = {"休日 日直", "休日 宿直", "平日 宿直"}
        assert all(r["Shift"] in valid_shifts for r in rows)

    def test_each_doctor_gap_constraint(self):
        doctors = ["医師A", "医師B", "医師C"]
        rows = self._make(doctors=doctors, gap_lo=5, gap_hi=8)
        from collections import defaultdict
        by_doc = defaultdict(list)
        for r in rows:
            by_doc[r["Doctor"]].append(r["Date"])
        for doc, dates in by_doc.items():
            assert ok_gap(sorted(dates), lo=5, hi=8), f"{doc} の日程がギャップ制約を満たしていません"

    def test_sorted_by_date_then_shift(self):
        rows = self._make()
        keys = [(r["Date"], r["Shift"]) for r in rows]
        assert keys == sorted(keys)

    def test_raises_when_impossible(self):
        doctors = [f"医師{i}" for i in range(50)]  # too many doctors for one month
        unavail = {d: set() for d in doctors}
        with pytest.raises(RuntimeError):
            make_schedule(2024, 6, doctors, unavail)
