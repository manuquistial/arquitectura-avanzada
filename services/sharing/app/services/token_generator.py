"""Token generator for shortlinks."""

import secrets
import string


class TokenGenerator:
    """Generates secure random tokens for shortlinks."""
    
    @staticmethod
    def generate_token(length: int = 12) -> str:
        """Generate a secure random token.
        
        Args:
            length: Token length (default 12)
            
        Returns:
            Random alphanumeric token
        """
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def generate_shortlink(base_url: str, token: str) -> str:
        """Generate full shortlink URL.
        
        Args:
            base_url: Base URL (e.g., https://carpeta.local)
            token: Token
            
        Returns:
            Full shortlink URL
        """
        return f"{base_url.rstrip('/')}/s/{token}"

