# SearXNG - Internal Search Engine

Privacy-respecting metasearch engine for internal use.

## Usage

### Web UI

Access at: http://localhost:8888

### JSON API

```bash
# Search with JSON response
curl "http://localhost:8888/search?q=your+query&format=json"
```

### From Python

```python
import httpx

async def search(query: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "http://searxng:8080/search",
            params={"q": query, "format": "json"}
        )
        data = resp.json()
        return data.get("results", [])
```

## Configuration

Edit `settings.yml` to:
- Enable/disable search engines
- Change default language
- Adjust UI theme

## Resources

- RAM: ~128 MB
- No additional containers required (Redis disabled)
- Documentation: https://docs.searxng.org
