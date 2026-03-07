from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
import hashlib
import json
import base64
from datetime import datetime

class CryptoEngine:

    @staticmethod
    def generate_keypair():
        """Generate a new Ed25519 keypair for an agent"""
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return {
            "private_key": private_bytes.decode(),
            "public_key": public_bytes.decode()
        }

    @staticmethod
    def sign_message(private_key_pem: str, message: dict) -> str:
        """Sign a message with agent's private key"""
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(), password=None
        )
        message_bytes = json.dumps(message, sort_keys=True).encode()
        signature = private_key.sign(message_bytes)
        return base64.b64encode(signature).decode()

    @staticmethod
    def verify_signature(public_key_pem: str, message: dict, signature: str) -> bool:
        """Verify a message signature from an agent"""
        try:
            public_key = serialization.load_pem_public_key(public_key_pem.encode())
            message_bytes = json.dumps(message, sort_keys=True).encode()
            signature_bytes = base64.b64decode(signature.encode())
            public_key.verify(signature_bytes, message_bytes)
            return True
        except InvalidSignature:
            return False
        except Exception:
            return False

    @staticmethod
    def hash_payload(payload: dict) -> str:
        """Create tamper-proof hash of any payload"""
        payload_str = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(payload_str.encode()).hexdigest()

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key for organizations"""
        import secrets
        return f"ta_{secrets.token_urlsafe(32)}"