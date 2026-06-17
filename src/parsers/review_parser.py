"""Parser for hotel review data extraction."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.monitoring.logger import get_logger
from src.parsers.base import BaseParser
from src.utils.validators import sanitize_text

logger = get_logger(__name__)


class ReviewParser(BaseParser):
    """Parser for extracting hotel review data.

    Handles review parsing across different sources with
    source-specific extraction patterns.
    """

    # Common review selectors across sources
    REVIEW_SELECTORS = {
        "booking": {
            "review_item": "[data-testid='review-submission']",
            "reviewer_name": "[data-testid='reviewer-name']",
            "review_score": "[data-testid='review-score']",
            "review_date": "[data-testid='review-date']",
            "review_title": "[data-testid='review-title']",
            "review_text": "[data-testid='review-text']",
            "review_positive": "[data-testid='review-positive']",
            "review_negative": "[data-testid='review-negative']",
            "reviewer_country": "[data-testid='reviewer-country']",
        },
        "agoda": {
            "review_item": ".Review-comment",
            "reviewer_name": ".Review-comment-reviewer",
            "review_score": ".Review-comment-leftHeader .Review-comment-score .Review-comment-scoreBadges",
            "review_date": ".Review-statusBar-date",
            "review_title": ".Review-comment-body .Review-comment-title",
            "review_text": ".Review-comment-bodyText",
            "review_positive": ".Review-comment-positive",
            "review_negative": ".Review-comment-negative",
            "reviewer_country": ".Review-comment-reviewerCountry",
        },
        "expedia": {
            "review_item": ".uitk-review",
            "reviewer_name": ".uitk-review-username",
            "review_score": ".uitk-review-score",
            "review_date": ".uitk-review-date",
            "review_title": ".uitk-review-title",
            "review_text": ".uitk-review-text",
            "review_positive": ".uitk-review-positive",
            "review_negative": ".uitk-review-negative",
            "reviewer_country": ".uitk-review-user-location",
        },
    }

    def __init__(self, source: str):
        super().__init__(source)
        self._selectors = self.REVIEW_SELECTORS.get(source, {})

    def parse_search_results(self, html, city, checkin_date, checkout_date):
        """Not used for review parser - implemented for base class."""
        return []

    def parse_hotel_detail(self, html: str, hotel_url: str) -> Dict[str, Any]:
        """Parse reviews from hotel detail page.

        Args:
            html: HTML content of hotel detail page
            hotel_url: URL of the hotel

        Returns:
            Dictionary with reviews list and summary
        """
        soup = self.parse_with_soup(html)
        reviews = []

        review_items = self.extract_list(
            soup, self._selectors.get("review_item", "")
        )

        for item in review_items:
            try:
                review = self._parse_review_item(item)
                if review:
                    reviews.append(review)
            except Exception as e:
                logger.debug(f"Failed to parse review: {e}")
                continue

        # Calculate summary statistics
        summary = self._calculate_summary(reviews)

        return {
            "reviews": reviews,
            "summary": summary,
            "total_reviews": len(reviews),
            "hotel_url": hotel_url,
        }

    def parse_reviews_page(self, html: str) -> List[Dict[str, Any]]:
        """Parse a dedicated reviews page.

        Args:
            html: HTML of reviews page

        Returns:
            List of review dictionaries
        """
        soup = self.parse_with_soup(html)
        reviews = []

        review_items = self.extract_list(
            soup, self._selectors.get("review_item", "")
        )

        for item in review_items:
            try:
                review = self._parse_review_item(item)
                if review:
                    reviews.append(review)
            except Exception as e:
                logger.debug(f"Failed to parse review: {e}")
                continue

        return reviews

    def _parse_review_item(self, item) -> Optional[Dict[str, Any]]:
        """Parse a single review element.

        Args:
            item: BeautifulSoup element for one review

        Returns:
            Review dictionary or None
        """
        review = {}

        # Reviewer name
        name = self.extract_text(item, self._selectors.get("reviewer_name", ""))
        if not name:
            return None
        review["reviewer_name"] = sanitize_text(name)

        # Review score
        score_text = self.extract_text(
            item, self._selectors.get("review_score", "")
        )
        review["score"] = self._parse_review_score(score_text)

        # Review date
        date_text = self.extract_text(
            item, self._selectors.get("review_date", "")
        )
        review["review_date"] = self._parse_review_date(date_text)

        # Review title
        review["title"] = sanitize_text(
            self.extract_text(item, self._selectors.get("review_title", ""))
        )

        # Review text
        review["text"] = sanitize_text(
            self.extract_text(item, self._selectors.get("review_text", ""))
        )

        # Positive/negative aspects
        review["positive"] = sanitize_text(
            self.extract_text(item, self._selectors.get("review_positive", ""))
        )
        review["negative"] = sanitize_text(
            self.extract_text(item, self._selectors.get("review_negative", ""))
        )

        # Reviewer country
        review["reviewer_country"] = sanitize_text(
            self.extract_text(
                item, self._selectors.get("reviewer_country", "")
            )
        )

        # Source
        review["source"] = self.source

        return review

    def _parse_review_score(self, text: str) -> float:
        """Parse review score from text.

        Args:
            text: Score text

        Returns:
            Score as float (0-10 scale)
        """
        if not text:
            return 0.0

        # Extract number
        match = re.search(r"(\d+[.,]?\d*)", text)
        if not match:
            return 0.0

        try:
            score = float(match.group(1).replace(",", "."))
        except ValueError:
            return 0.0

        # Normalize
        if "/5" in text:
            return score * 2
        elif "/10" in text or score <= 10:
            return score
        elif "%" in text:
            return score / 10

        return min(10.0, score)

    def _parse_review_date(self, text: str) -> Optional[str]:
        """Parse review date from text.

        Args:
            text: Date text

        Returns:
            ISO format date string or None
        """
        if not text:
            return None

        # Common date formats
        formats = [
            "%B %d, %Y",
            "%d %B %Y",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%b %d, %Y",
            "%d %b %Y",
        ]

        text = text.strip()
        # Remove prefixes like "Reviewed: " or "Date: "
        text = re.sub(r"^(Reviewed:|Date:|Posted:|Submitted:)\s*", "", text, flags=re.I)

        for fmt in formats:
            try:
                dt = datetime.strptime(text, fmt)
                return dt.date().isoformat()
            except ValueError:
                continue

        # Try relative dates
        text_lower = text.lower()
        if "today" in text_lower:
            return datetime.now().date().isoformat()
        elif "yesterday" in text_lower:
            from datetime import timedelta
            return (datetime.now() - timedelta(days=1)).date().isoformat()

        return None

    def _calculate_summary(self, reviews: List[Dict]) -> Dict[str, Any]:
        """Calculate summary statistics from reviews.

        Args:
            reviews: List of review dictionaries

        Returns:
            Summary dictionary
        """
        if not reviews:
            return {
                "average_score": 0.0,
                "score_distribution": {},
                "total_reviews": 0,
            }

        scores = [r["score"] for r in reviews if r.get("score", 0) > 0]

        # Score distribution
        distribution = {}
        for score in scores:
            bucket = int(score)
            distribution[bucket] = distribution.get(bucket, 0) + 1

        return {
            "average_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
            "score_distribution": distribution,
            "total_reviews": len(reviews),
            "reviews_with_scores": len(scores),
        }
