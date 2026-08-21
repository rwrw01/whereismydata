from pydantic import BaseModel, Field


class LookupRequest(BaseModel):
    hostnames: list[str] = Field(..., min_length=1, max_length=200)


class LookupResult(BaseModel):
    hostname: str
    asn: int | None
    org_name: str | None
    org_country: str | None


class LookupResponse(BaseModel):
    results: list[LookupResult]
