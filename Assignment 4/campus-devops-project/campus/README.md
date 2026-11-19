# Smart Campus Facility Platform - Testing and DevOps (CSA1012 Assignment 4)

Name: Muthu Krishnan K | Reg No: 192511039 | Course: CSA1012 Software Engineering

Small Flask + SQLite service (bookings, approvals, tickets, sensor events) with unit, integration,
regression, security and migration tests, a GitHub Actions pipeline and a Dockerfile.

## Run
    pip install -r requirements.txt
    python3 -m unittest discover -s tests -t . -v     # 37 tests
    python3 scripts/load_test.py                      # concurrency check, expects double_booked_slots=0
    ./scripts/pipeline.sh                             # local pipeline runner
    MIGRATE=1 ./scripts/pipeline.sh                   # deploy with v2 migration
    MIGRATE=1 FAIL_MIGRATION=1 ./scripts/pipeline.sh  # failed deploy + rollback rehearsal

Folders: app/ (service), tests/, scripts/, evidence/ (saved run logs), .github/workflows/ci.yml, Dockerfile.
