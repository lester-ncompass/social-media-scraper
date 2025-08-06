import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from src.models.scrape import ScrapeRequest
from src.services.facebook_scraper import FacebookScraperService
from src.services.instagram_scraper import InstagramScraperService
from src.services.rate_social_media import RateSocialMediaService
from src.services.result_feedback import ResultFeedbackService
from src.services.tiktok_scraper import TiktokScraperService
from src.services.x_scraper import XScraperService

logger = logging.getLogger(__name__)
rateSocialMediaService = RateSocialMediaService()
resultFeedbackService = ResultFeedbackService()


router = APIRouter(
    prefix="/scrape",
    tags=["scrape"],
)


@router.post(
    "",
    tags=["scrape"],
)
async def scrape(
    data: ScrapeRequest,
) -> JSONResponse:
    """Scrape endpoint for processing scrape data.

    Args:
        data (ScrapeRequest): ScrapeRequest content
    Returns:
        JSONResponse: Object containing the data, status code, and error message.
    """

    facebook = FacebookScraperService()
    instagram = InstagramScraperService()
    tiktok = TiktokScraperService()
    x = XScraperService()
    log = logger.getChild("scrape")
    log.debug(f"Received data: {data}")
    # This will be used for concurrent scraping
    # facebook_results, instagram_results, tiktok_results, x_results = (
    #     await asyncio.gather(
    #         facebook.scrape(url=data.facebook, timeout=2000),
    #         instagram.scrape(url=data.instagram, timeout=2000),
    #         tiktok.scrape(url=data.tiktok, timeout=2000),
    #         x.scrape(url=data.x, timeout=2000),
    #     )
    # )

    # This will be used for sequential scraping
    facebook_results = await facebook.scrape(url=data.facebook, timeout=2000)
    instagram_results = await instagram.scrape(url=data.instagram, timeout=2000)
    tiktok_results = await tiktok.scrape(
        url=data.tiktok, timeout=2000
    )  # This is playwright scraping  # noqa
    # tiktok_results = await tiktok.scrape_via_httpx(url=data.tiktok, timeout=2000)
    x_results = await x.scrape(url=data.x, timeout=2000)
    gathered_data = {
        "facebook": facebook_results,
        "instagram": instagram_results,
        "tiktok": tiktok_results,
        "x": x_results,
    }

    scores = rateSocialMediaService.rate(gathered_data)
    feedback = await resultFeedbackService.generate_feedback(gathered_data, scores)
    log.info("Generated scores: %s, feedback: %s", scores, feedback)
    results = {**scores, "feedback": feedback}

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "data": results,
            "status_code": status.HTTP_200_OK,
        },
    )
