import os
import httpx

SERPER_API_KEY = os.getenv("SERPER_API_KEY")


async def search_web(query: str):
    api_key = SERPER_API_KEY or os.getenv("SERPER_API_KEY")
    if not api_key:
        return {"status": "NOT_CONNECTED", "data": []}

    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "q": query,
        "num": 10,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                results = [
                    {
                        "title": item.get("title"),
                        "link": item.get("link"),
                        "snippet": item.get("snippet"),
                    }
                    for item in data.get("organic", [])
                ]
                return {"status": "LIVE", "data": results}
            return {"status": "ERROR", "data": []}
    except Exception as exc:
        return {"status": "ERROR", "error": str(exc), "data": []}
