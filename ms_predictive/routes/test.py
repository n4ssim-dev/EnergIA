import httpx


url = (
    "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
    "temperature-quotidienne-regionale/records"
)

where = "date in [date'2025-01-01'..date'2025-01-31']"

response = httpx.get(
    url,
    params={
        "where": where,
        "limit": 100,
        "order_by": "date DESC",
    }
)

response.raise_for_status()

resultats = response.json()["results"]

for ligne in resultats[:20]:
    print(
        ligne.get("date"),
        ligne.get("nom_region")
    )