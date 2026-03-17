"""SSL configuration and warning suppression."""
import urllib3
import warnings

def disable_ssl_warnings():
    """Disable urllib3 SSL warnings (for development only)."""
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")

# Auto-disable on import
disable_ssl_warnings()