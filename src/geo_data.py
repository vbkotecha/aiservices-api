import urllib.request
import json
from fastapi import HTTPException

def get_ip_geo(ip: str):
    """Get geolocation data for an IP address using free ipapi.co API."""
    try:
        url = "https://ipapi.co/" + ip + "/json/"
        req = urllib.request.Request(url, headers={"User-Agent": "AgentServices/1.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        if data.get("error"):
            raise HTTPException(status_code=400, detail=data.get("reason", "IP lookup failed"))
        return {
            "ip": data.get("ip"),
            "city": data.get("city"),
            "region": data.get("region"),
            "country": data.get("country_name"),
            "country_code": data.get("country"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "timezone": data.get("timezone"),
            "postal": data.get("postal"),
            "org": data.get("org"),
            "asn": data.get("asn"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))