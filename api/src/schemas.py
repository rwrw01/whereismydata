from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

# 253 is the maximum length of a fully qualified DNS name. The character class
# bounds obviously-invalid input (whitespace, control chars, URL/path fragments)
# without attempting to be a full RFC 1035 validator.
Hostname = Annotated[
    str,
    StringConstraints(min_length=1, max_length=253, pattern=r"^[A-Za-z0-9._-]+$"),
]


class LookupRequest(BaseModel):
    hostnames: list[Hostname] = Field(..., min_length=1, max_length=200)


class LookupResult(BaseModel):
    hostname: str
    asn: int | None
    org_name: str | None
    org_country: str | None
    org_country_source: str | None


class LookupResponse(BaseModel):
    results: list[LookupResult]
