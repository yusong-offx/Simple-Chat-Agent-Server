import httpx

from ipaddress import ip_address
from pydantic import BaseModel, IPvAnyAddress, Field
from pydantic_extra_types.timezone_name import TimeZoneName
from datetime import datetime
from zoneinfo import ZoneInfo
from langchain_core.tools import tool


class IpInfoResponse(BaseModel):
    requested_ip: IPvAnyAddress = Field(description="request ip parameter")
    latitude: float = Field(description="request ip's latitue")
    longitude: float = Field(description="request ip's longitude")
    timezone: TimeZoneName = Field(description="request ip's timezone name")
    current_time_with_timezone: datetime = Field(
        description="request ip's current time with timezone"
    )


@tool("ip_info")
async def get_ip_info(request_ip: str) -> IpInfoResponse:
    """Look up geolocation and local time for an IP address.

    Queries ip-api.com to obtain latitude, longitude, and IANA timezone for the
    provided IPv4/IPv6 address. Loopback addresses (127.0.0.1, ::1) are resolved
    to 8.8.8.8 before lookup. Returns a JSON string suitable for LLM consumption.

    Args:
        request_ip (str): Target IPv4/IPv6 address to look up. If a loopback
            address is provided, it is replaced with 8.8.8.8.

    Returns:
        str: JSON string with fields: requested_ip, latitude, longitude, timezone,
            current_time_with_timezone (ISO 8601).

    Raises:
        httpx.HTTPStatusError: Non-2xx HTTP status from ip-api.com.
        ValueError: Invalid IP string.
        Exception: Any other runtime error during lookup.
    """
    ip_obj = ip_address(request_ip)

    # if localhost, request_ip -> google dns ip
    if ip_obj.is_loopback:
        ip_obj = ip_address("8.8.8.8")

    try:
        # fetch "ip-api.com"
        # body : lat, lon, tz
        async with httpx.AsyncClient() as client:
            api_url = f"http://ip-api.com/json/{ip_obj}?fields=status,message,lat,lon,timezone,query"
            response = await client.get(api_url)
            response.raise_for_status()  # 200 OK가 아니면 오류 발생
            data = response.json()

        if data.get("status") != "success":
            error_message = data.get("message", "Failed to fetch IP info")
            raise Exception(f"{error_message} (request ip : {ip_obj})")

        tz = ZoneInfo(data["timezone"])
        current_time_in_timezone = datetime.now(tz)

        return IpInfoResponse(
            requested_ip=data.get("query", ip_obj),
            latitude=data["lat"],
            longitude=data["lon"],
            timezone=data["timezone"],
            current_time_with_timezone=current_time_in_timezone,
        ).model_dump_json()

    except Exception as e:
        raise e
