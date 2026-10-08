from datetime import datetime, timezone

import pytest

from jobfinder.adapters import parse_ashbyhq, parse_greenhouse, parse_lever
from jobfinder.models import Job, Target


ASHBY_TARGET = Target(
    ats="ashbyhq",
    name="Acme",
    token="acme",
    endpoint="https://api.ashbyhq.com/posting-api/job-board/{token}",
)

GREENHOUSE_TARGET = Target(
    ats="greenhouse",
    name="Acme",
    token="acme",
    endpoint="https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
)

LEVER_TARGET = Target(
    ats="lever",
    name="Acme",
    token="acme",
    endpoint="https://api.lever.co/v0/postings/{token}",
)


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def ashby_job(**overrides) -> Job:
    defaults = {
        "ats": "ashbyhq",
        "company": "Acme",
        "company_token": "acme",
        "job_id": "a1",
        "title": "Dev",
        "location": "Paris",
        "url": "https://example.com/a1",
        "published_at": None,
        "updated_at": None,
        "description": None,
    }
    return Job(**{**defaults, **overrides})


def greenhouse_job(**overrides) -> Job:
    defaults = {
        "ats": "greenhouse",
        "company": "Acme",
        "company_token": "acme",
        "job_id": "123",
        "title": "Python Developer",
        "location": "Paris",
        "url": "https://example.com/jobs/123",
        "published_at": None,
        "updated_at": None,
        "description": None,
    }
    return Job(**{**defaults, **overrides})


def lever_job(**overrides) -> Job:
    defaults = {
        "ats": "lever",
        "company": "Acme",
        "company_token": "acme",
        "job_id": "l1",
        "title": "Dev",
        "location": "Paris",
        "url": "https://example.com/l1",
        "published_at": utc(2026, 9, 23, 9, 13, 8, 619000),
        "updated_at": None,
        "description": "",
    }
    return Job(**{**defaults, **overrides})


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        pytest.param(
            "ashbyhq/single_job.json",
            [
                ashby_job(
                    published_at=utc(2026, 8, 14, 15, 17, 23, 480000),
                    description="Plain text",
                )
            ],
            id="plain-description-wins-over-html",
        ),
        pytest.param(
            "ashbyhq/secondary_locations.json",
            [
                ashby_job(
                    location="Paris,London,Berlin",
                    description="Plain text",
                )
            ],
            id="secondary-locations-are-appended",
        ),
        pytest.param(
            "ashbyhq/html_description_fallback.json",
            [ashby_job(description="Hello\nworld")],
            id="html-description-fallback",
        ),
        pytest.param(
            "ashbyhq/minimal_job.json",
            [ashby_job(description=None, published_at=None)],
            id="missing-optional-fields-become-none",
        ),
        pytest.param(
            "ashbyhq/empty_board.json",
            [],
            id="empty-board",
        ),
        pytest.param(
            "ashbyhq/mixed_locations.json",
            [
                ashby_job(
                    title="Paris job",
                    description="One",
                ),
                ashby_job(
                    job_id="a2",
                    title="London job",
                    location="London",
                    url="https://example.com/a2",
                    description="Two",
                ),
            ],
            id="parser-does-not-filter-locations",
        ),
    ],
)
def test_parse_ashbyhq(load_fixture, fixture, expected):
    payload = load_fixture(fixture)

    assert list(parse_ashbyhq(payload, ASHBY_TARGET)) == expected


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        pytest.param(
            "greenhouse/single_job.json",
            [
                greenhouse_job(
                    published_at=utc(2026, 8, 14, 15, 17, 23),
                    updated_at=utc(2026, 9, 2, 9, 38, 47),
                    description="Hello\nworld",
                )
            ],
            id="html-description-and-dates",
        ),
        pytest.param(
            "greenhouse/minimal_job.json",
            [greenhouse_job(location=None, url=None)],
            id="missing-optional-fields",
        ),
        pytest.param(
            "greenhouse/empty_board.json",
            [],
            id="empty-board",
        ),
        pytest.param(
            "greenhouse/mixed_locations.json",
            [
                greenhouse_job(
                    title="Paris job",
                    url="https://example.com/jobs/123",
                    description="One",
                ),
                greenhouse_job(
                    job_id="456",
                    title="London job",
                    location="London",
                    url="https://example.com/jobs/456",
                    description="Two",
                ),
            ],
            id="parser-does-not-filter-locations",
        ),
    ],
)
def test_parse_greenhouse(load_fixture, fixture, expected):
    payload = load_fixture(fixture)

    assert list(parse_greenhouse(payload, GREENHOUSE_TARGET)) == expected


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        pytest.param(
            "lever/plain_fields.json",
            [
                lever_job(
                    location="Paris,Lyon",
                    description="Intro\nBody\nPerks\nGym\nFooter",
                )
            ],
            id="plain-fields-and-lists-are-joined",
        ),
        pytest.param(
            "lever/html_fallback.json",
            [lever_job(description="Intro\nBody\nFooter")],
            id="html-fields-fallback",
        ),
        pytest.param(
            "lever/minimal_posting.json",
            [
                lever_job(
                    location="",
                    url=None,
                    published_at=None,
                    description="",
                )
            ],
            id="missing-optional-fields",
        ),
        pytest.param(
            "lever/empty_list.json",
            [],
            id="empty-list",
        ),
        pytest.param(
            "lever/mixed_locations.json",
            [
                lever_job(
                    title="Paris job",
                    published_at=None,
                    description="One",
                ),
                lever_job(
                    job_id="l2",
                    title="London job",
                    location="London",
                    url="https://example.com/l2",
                    published_at=None,
                    description="Two",
                ),
            ],
            id="parser-does-not-filter-locations",
        ),
    ],
)
def test_parse_lever(load_fixture, fixture, expected):
    payload = load_fixture(fixture)

    assert list(parse_lever(payload, LEVER_TARGET)) == expected
