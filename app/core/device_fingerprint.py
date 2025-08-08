import hashlib
import json
from typing import Dict, Any, Optional
from user_agents import parse
import ipaddress
import requests
from fastapi import Request

class DeviceFingerprint:
    """Utility class for device fingerprinting and validation"""
    
    @staticmethod
    def create_device_hash(user_agent: str, screen_resolution: Optional[str] = None, 
                          timezone: Optional[str] = None, language: Optional[str] = None) -> str:
        """
        Create a unique device hash from device characteristics
        
        Args:
            user_agent: Browser user agent string
            screen_resolution: Screen resolution (e.g., "1920x1080")
            timezone: Timezone (e.g., "America/New_York")
            language: Browser language (e.g., "en-US")
            
        Returns:
            SHA-256 hash of device fingerprint
        """
        # Parse user agent to extract device info
        ua = parse(user_agent)
        
        # Create fingerprint data
        fingerprint_data = {
            "browser": ua.browser.family,
            "browser_version": ua.browser.version_string,
            "os": ua.os.family,
            "os_version": ua.os.version_string,
            "device": ua.device.family,
            "screen_resolution": screen_resolution,
            "timezone": timezone,
            "language": language,
            "is_mobile": ua.is_mobile,
            "is_tablet": ua.is_tablet,
            "is_pc": ua.is_pc
        }
        
        # Create hash from fingerprint data
        fingerprint_json = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_json.encode()).hexdigest()
    
    @staticmethod
    def get_device_name(user_agent: str) -> str:
        """Generate a human-readable device name from user agent"""
        ua = parse(user_agent)
        
        if ua.is_mobile:
            device_type = "Mobile"
        elif ua.is_tablet:
            device_type = "Tablet"
        else:
            device_type = "Desktop"
        
        os_name = ua.os.family if ua.os.family != "Other" else "Unknown OS"
        browser_name = ua.browser.family if ua.browser.family != "Other" else "Unknown Browser"
        
        return f"{device_type} - {os_name} - {browser_name}"
    
    @staticmethod
    def get_location_from_ip(ip_address: str) -> Dict[str, Any]:
        """
        Get location information from IP address
        
        Args:
            ip_address: IP address to geolocate
            
        Returns:
            Dictionary with location information
        """
        try:
            # Skip private IP addresses
            if ipaddress.ip_address(ip_address).is_private:
                return {
                    "country": "Unknown",
                    "country_code": "XX",
                    "city": "Unknown",
                    "location": "Private Network"
                }
            
            # Use free IP geolocation service (in production, use a paid service)
            response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    return {
                        "country": data.get("country", "Unknown"),
                        "country_code": data.get("countryCode", "XX"),
                        "city": data.get("city", "Unknown"),
                        "location": f"{data.get('city', 'Unknown')}, {data.get('country', 'Unknown')}"
                    }
        except Exception:
            pass
        
        return {
            "country": "Unknown",
            "country_code": "XX",
            "city": "Unknown",
            "location": "Unknown"
        }
    
    @staticmethod
    def extract_device_info_from_request(request: Request) -> Dict[str, Any]:
        """
        Extract device information from FastAPI request
        
        Args:
            request: FastAPI request object
            
        Returns:
            Dictionary with device information
        """
        user_agent = request.headers.get("user-agent", "")
        client_ip = request.client.host if request.client else "unknown"
        
        # Get location from IP
        location_info = DeviceFingerprint.get_location_from_ip(client_ip)
        
        # Create device hash
        device_hash = DeviceFingerprint.create_device_hash(user_agent)
        
        # Generate device name
        device_name = DeviceFingerprint.get_device_name(user_agent)
        
        return {
            "user_agent": user_agent,
            "ip_address": client_ip,
            "device_hash": device_hash,
            "device_name": device_name,
            "country": location_info["country"],
            "country_code": location_info["country_code"],
            "city": location_info["city"],
            "location": location_info["location"]
        }
    
    @staticmethod
    def validate_device_fingerprint(stored_hash: str, current_hash: str) -> bool:
        """
        Validate if current device fingerprint matches stored fingerprint
        
        Args:
            stored_hash: Hash stored in database
            current_hash: Hash from current request
            
        Returns:
            True if fingerprints match, False otherwise
        """
        return stored_hash == current_hash 