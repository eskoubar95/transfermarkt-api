import uvicorn
from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.responses import RedirectResponse

from app.api.api import api_router
from app.services.base import TransfermarktBase
from app.settings import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMITING_FREQUENCY],
    enabled=settings.RATE_LIMITING_ENABLE,
)
app = FastAPI(title="Transfermarkt API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.include_router(api_router)


@app.get("/health", tags=["Health"])
def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "transfermarkt-api"}


@app.get("/monitoring/anti-scraping", tags=["Monitoring"])
def get_anti_scraping_stats():
    """
    Get comprehensive anti-scraping monitoring statistics.

    Returns detailed metrics about:
    - Request success/failure rates
    - Block detection
    - Session and retry performance
    - Response times and uptime
    """
    return TransfermarktBase.get_monitoring_stats()


@app.get("/monitoring/session", tags=["Monitoring"])
def get_session_stats():
    """Get session manager statistics."""
    return TransfermarktBase.get_session_stats()


@app.get("/monitoring/retry", tags=["Monitoring"])
def get_retry_stats():
    """Get retry manager configuration and statistics."""
    return TransfermarktBase.get_retry_stats()


@app.get("/test/browser-scraping", tags=["Testing"])
def test_browser_scraping(url: str = "https://httpbin.org/html", full: bool = False):
    """Test browser scraping capabilities with specified URL."""
    try:
        import asyncio

        from app.services.base import _browser_scraper

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Test with specified URL
        result = loop.run_until_complete(
            _browser_scraper.scrape_with_browser(url),
        )

        if full:
            return {
                "status": "success",
                "url": url,
                "content": result,
            }
        else:
            return {
                "status": "success",
                "url": url,
                "content_length": len(result),
                "has_transfermarkt": "transfermarkt" in result.lower(),
                "preview": result[:500] + "..." if len(result) > 500 else result,
            }
    except Exception as e:
        return {
            "status": "error",
            "url": url,
            "error": str(e),
        }


@app.get("/debug/xpath", tags=["Debug"])
def debug_xpath(url: str = "https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query=Barcelona&Verein_page=1"):
    """Debug XPath extraction for club search."""
    try:
        from app.services.clubs.search import TransfermarktClubSearch
        from app.utils.xpath import Clubs

        # Create instance and get data
        tfmkt = TransfermarktClubSearch(query="Barcelona", page_number=1)

        # Get raw XPath results
        clubs_names = tfmkt.get_list_by_xpath(Clubs.Search.NAMES)
        clubs_urls = tfmkt.get_list_by_xpath(Clubs.Search.URLS)
        clubs_countries = tfmkt.get_list_by_xpath(Clubs.Search.COUNTRIES)
        clubs_squads = tfmkt.get_list_by_xpath(Clubs.Search.SQUADS)
        clubs_market_values = tfmkt.get_list_by_xpath(Clubs.Search.MARKET_VALUES)

        return {
            "xpath_results": {
                "names": clubs_names,
                "urls": clubs_urls,
                "countries": clubs_countries,
                "squads": clubs_squads,
                "market_values": clubs_market_values,
            },
            "counts": {
                "names": len(clubs_names),
                "urls": len(clubs_urls),
                "countries": len(clubs_countries),
                "squads": len(clubs_squads),
                "market_values": len(clubs_market_values),
            },
            "xpath_definitions": {
                "NAMES": Clubs.Search.NAMES,
                "URLS": Clubs.Search.URLS,
                "COUNTRIES": Clubs.Search.COUNTRIES,
                "SQUADS": Clubs.Search.SQUADS,
                "MARKET_VALUES": Clubs.Search.MARKET_VALUES,
            },
        }
    except Exception as e:
        return {
            "error": str(e),
            "traceback": __import__("traceback").format_exc(),
        }


@app.get("/", include_in_schema=False)
def docs_redirect():
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
