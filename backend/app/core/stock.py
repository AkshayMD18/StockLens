from typing import Any

import httpx

SCREENER_URL = "https://api.patternsradar.com/v1/scan"


async def screen_stocks(
    source: str,
    universe: int = 500,
    limit: int = 20,
) -> Any:
    """Run a PatternsRadar Sift scan anonymously."""
    if not source.strip():
        raise ValueError("Scan source cannot be empty")
    if not 100 <= universe <= 9999:
        raise ValueError("Universe must be between 100 and 9999")
    if not 1 <= limit <= 2000:
        raise ValueError("Limit must be between 1 and 2000")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                SCREENER_URL,
                json={"source": source, "universe": universe, "limit": limit},
            )

            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as error:
        raise RuntimeError(
            f"PatternsRadar scan failed: HTTP {error.response.status_code}"
        ) from error

    except httpx.RequestError as error:
        raise RuntimeError("PatternsRadar scan request failed") from error
