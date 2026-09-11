import httpx

ODRE_TEMPERATURE_URL = (
    "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
    "temperature-quotidienne-regionale/records"
)

dates_a_verifier = [
    "2021-04-30",
    "2022-07-31",
    "2022-08-31",
    "2023-01-31",
    "2023-02-28",
    "2023-08-31",
    "2023-10-31",
    "2024-03-31",
    "2024-04-30",
    "2024-05-31",
    "2024-06-30",
    "2024-07-31",
    "2024-08-31",
    "2024-09-30",
    "2024-10-31",
    "2024-11-30",
    "2024-12-30",
    "2024-12-31",
    "2025-01-31",
    "2025-02-28",
    "2025-03-31",
    "2025-04-30",
    "2025-05-31",
    "2025-06-30",
    "2025-07-31",
    "2025-08-31",
    "2025-09-30",
    "2025-10-31",
    "2025-11-30",
    "2025-12-31",
    "2026-01-31",
    "2026-02-28",
    "2026-03-31",
    "2026-04-30",
    "2026-05-31",
    "2026-06-30",
    "2026-08-31",
    "2026-09-01",
    "2026-09-02",
    "2026-09-03",
    "2026-09-04"
]

with httpx.Client(timeout=30.0) as client:

    for date_test in dates_a_verifier:

        where = f"date = date'{date_test}'"

        response = client.get(
            ODRE_TEMPERATURE_URL,
            params={
                "where": where,
                "limit": 100,
            },
        )

        response.raise_for_status()

        resultats = response.json().get("results", [])

        print(
            date_test,
            "->",
            len(resultats),
            "lignes trouvées"
        )