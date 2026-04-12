"""
Encryption Manager

Handles AES-256 encryption with PBKDF2 key derivation for
sensitive data storage and protection.
"""

import logging
import os
from typing import Optional, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import base64


logger = logging.getLogger(__name__)


class EncryptionManager:
    """
    Manages encryption and decryption of sensitive data.
    
    Features:
    - AES-256 encryption with Fernet
    - PBKDF2 key derivation from password
    - Secure key storage
    - Key rotation mechanism
    """

    def __init__(self, password: Optional[str] = None):
        """
        Initialize encryption manager.

        Args:
            password: Master password for key derivation
        """
        self.password = password
        self.cipher_suite: Optional[Fernet] = None
        self.salt: Optional[bytes] = None

        if password:
            self._initialize_cipher(password)

    def _initialize_cipher(self, password: str) -> None:
        """
        Initialize cipher with password.

        Args:
            password: Master password
        """
        try:
            # Generate or use existing salt
            if not self.salt:
                self.salt = os.urandom(16)

            # Derive key from password
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self.salt,
                iterations=100000,
                backend=default_backend()
            )

            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            self.cipher_suite = Fernet(key)

            logger.info("Encryption cipher initialized")
        except Exception as e:
            logger.error(f"Failed to initialize cipher: {e}")
            raise

    def encrypt_data(self, plaintext: str) -> str:
        """
        Encrypt plaintext data.

        Args:
            plaintext: Data to encrypt

        Returns:
            Encrypted data (base64 encoded)
        """
        if not self.cipher_suite:
            logger.error("Cipher not initialized")
            return plaintext

        try:
            ciphertext = self.cipher_suite.encrypt(plaintext.encode())
            return base64.b64encode(ciphertext).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt_data(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext data.

        Args:
            ciphertext: Encrypted data (base64 encoded)

        Returns:
            Decrypted plaintext
        """
        if not self.cipher_suite:
            logger.error("Cipher not initialized")
            return ciphertext

        try:
            encrypted_data = base64.b64decode(ciphertext.encode())
            plaintext = self.cipher_suite.decrypt(encrypted_data)
            return plaintext.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def store_encrypted(self, key: str, data: str, storage: dict) -> None:
        """
        Store encrypted data in storage dictionary.

        Args:
            key: Storage key
            data: Data to encrypt and store
            storage: Storage dictionary
        """
        try:
            encrypted = self.encrypt_data(data)
            storage[key] = encrypted
            logger.debug(f"Data stored encrypted: {key}")
        except Exception as e:
            logger.error(f"Failed to store encrypted data: {e}")

    def retrieve_encrypted(self, key: str, storage: dict) -> Optional[str]:
        """
        Retrieve and decrypt data from storage.

        Args:
            key: Storage key
            storage: Storage dictionary

        Returns:
            Decrypted data or None if not found
        """
        try:
            if key not in storage:
                logger.warning(f"Key not found in storage: {key}")
                return None

            encrypted = storage[key]
            decrypted = self.decrypt_data(encrypted)
            logger.debug(f"Data retrieved and decrypted: {key}")
            return decrypted
        except Exception as e:
            logger.error(f"Failed to retrieve encrypted data: {e}")
            return None

    def rotate_encryption_keys(self, new_password: str, storage: dict) -> bool:
        """
        Rotate encryption keys with new password.

        Args:
            new_password: New master password
            storage: Storage dictionary with encrypted data

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Starting key rotation...")

            # Decrypt all data with old key
            decrypted_data = {}
            for key, encrypted_value in storage.items():
                try:
                    decrypted_data[key] = self.decrypt_data(encrypted_value)
                except Exception as e:
                    logger.error(f"Failed to decrypt {key} during rotation: {e}")
                    return False

            # Initialize new cipher
            self.password = new_password
            self.salt = os.urandom(16)
            self._initialize_cipher(new_password)

            # Re-encrypt all data with new key
            for key, plaintext in decrypted_data.items():
                try:
                    encrypted = self.encrypt_data(plaintext)
                    storage[key] = encrypted
                except Exception as e:
                    logger.error(f"Failed to re-encrypt {key} during rotation: {e}")
                    return False

            logger.info("Key rotation completed successfully")
            return True

        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            return False

    def get_status(self) -> dict:
        """Get encryption manager status"""
        return {
            "cipher_initialized": self.cipher_suite is not None,
            "has_password": self.password is not None,
            "salt_length": len(self.salt) if self.salt else 0
        }
