import pytest
from starlette.testclient import TestClient

from oncall_app.oncall_app import app

client = TestClient(app)


class TestApiCalendar:
    def test_returns_200(self):
        res = client.post("/api/calendar", data={
            "year": 2024, "month": 6, "docs": "医師A,医師B,医師C",
            "gap_lo": 5, "gap_hi": 8,
        })
        assert res.status_code == 200

    def test_response_structure(self):
        res = client.post("/api/calendar", data={
            "year": 2024, "month": 6, "docs": "医師A,医師B",
            "gap_lo": 5, "gap_hi": 8,
        })
        data = res.json()
        assert data["year"] == 2024
        assert data["month"] == 6
        assert data["docs"] == ["医師A", "医師B"]
        assert data["gap_lo"] == 5
        assert data["gap_hi"] == 8
        assert isinstance(data["weeks"], list)

    def test_weeks_is_list_of_weeks(self):
        res = client.post("/api/calendar", data={
            "year": 2024, "month": 6, "docs": "医師A",
            "gap_lo": 5, "gap_hi": 8,
        })
        weeks = res.json()["weeks"]
        assert len(weeks) > 0
        for week in weeks:
            assert len(week) == 7

    def test_day_fields(self):
        res = client.post("/api/calendar", data={
            "year": 2024, "month": 6, "docs": "医師A",
            "gap_lo": 5, "gap_hi": 8,
        })
        weeks = res.json()["weeks"]
        day = weeks[0][0]
        assert "date" in day
        assert "day" in day
        assert "month" in day
        assert "weekday" in day
        assert "is_holiday" in day
        assert "in_month" in day

    def test_docs_whitespace_trimmed(self):
        res = client.post("/api/calendar", data={
            "year": 2024, "month": 6, "docs": " 医師A , 医師B ",
            "gap_lo": 5, "gap_hi": 8,
        })
        assert res.json()["docs"] == ["医師A", "医師B"]


class TestApiSchedule:
    def _post_schedule(self, unavail=""):
        return client.post("/api/schedule", data={
            "year": 2024, "month": 6,
            "docs": "医師A,医師B,医師C",
            "unavail": unavail,
            "gap_lo": 5, "gap_hi": 8,
        })

    def test_returns_200(self):
        res = self._post_schedule()
        assert res.status_code == 200

    def test_response_has_rows_and_tok(self):
        data = self._post_schedule().json()
        assert "rows" in data
        assert "tok" in data
        assert isinstance(data["rows"], list)
        assert isinstance(data["tok"], str)

    def test_rows_structure(self):
        rows = self._post_schedule().json()["rows"]
        assert len(rows) > 0
        for r in rows:
            assert set(r.keys()) == {"Date", "Shift", "Doctor"}

    def test_each_doctor_has_4_shifts(self):
        from collections import Counter
        rows = self._post_schedule().json()["rows"]
        counts = Counter(r["Doctor"] for r in rows)
        for doc in ["医師A", "医師B", "医師C"]:
            assert counts[doc] == 4

    def test_impossible_schedule_returns_error(self):
        many_docs = ",".join([f"医師{i}" for i in range(50)])
        res = client.post("/api/schedule", data={
            "year": 2024, "month": 6,
            "docs": many_docs,
            "unavail": "",
            "gap_lo": 5, "gap_hi": 8,
        })
        assert res.status_code == 422
        assert "error" in res.json()


class TestCsvDownload:
    def _get_tok(self):
        res = client.post("/api/schedule", data={
            "year": 2024, "month": 6,
            "docs": "医師A,医師B,医師C",
            "unavail": "",
            "gap_lo": 5, "gap_hi": 8,
        })
        return res.json()["tok"]

    def test_csv_download_ok(self):
        tok = self._get_tok()
        res = client.get(f"/csv?tok={tok}")
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]

    def test_csv_content_has_header(self):
        tok = self._get_tok()
        res = client.get(f"/csv?tok={tok}")
        text = res.content.decode("utf-8-sig")
        assert "Date" in text
        assert "Shift" in text
        assert "Doctor" in text

    def test_invalid_tok_returns_404(self):
        res = client.get("/csv?tok=invalidtoken")
        assert res.status_code == 404


class TestSpaRoutes:
    def test_root_returns_html(self):
        res = client.get("/")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]

    def test_calendar_route_returns_html(self):
        res = client.get("/calendar")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]

    def test_schedule_route_returns_html(self):
        res = client.get("/schedule")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]
