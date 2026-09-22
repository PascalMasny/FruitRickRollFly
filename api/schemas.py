"""Request and response shapes.

Only the request is modelled strictly. Responses are assembled as plain dicts
by the services, because the timeline is a large, uniform numeric payload and
running it through a validator per percept buys nothing.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    url: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description=(
            "A link to one video on YouTube, TikTok or Instagram. Anything "
            "else is rejected; see api.services.sources."
        ),
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
    )


class AnalysisAccepted(BaseModel):
    id: str
    stage: str
    events: str = Field(description="Server-sent events stream for this job.")
