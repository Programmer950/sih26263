"""Storage Service for Secure File Ingestion and Verification."""

import os
import uuid
import hashlib
from typing import BinaryIO, Tuple
from app.core.config import settings


class FileSizeExceededError(ValueError):
    """Raised when uploaded file exceeds streaming size limit."""
    pass


class InvalidFileFormatError(ValueError):
    """Raised when file content fails magic bytes verification."""
    pass


class PathTraversalError(SecurityError if "SecurityError" in globals() else ValueError):
    """Raised when storage path traversal is attempted."""
    pass


class StorageService:
    """
    Handles streaming file storage, SHA-256 fingerprinting,
    path-traversal protection, and restrictive filesystem permissions.
    """

    @classmethod
    def ensure_upload_dir(cls) -> str:
        """Ensures the upload directory exists outside or in designated backend path."""
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        return upload_dir

    @classmethod
    def resolve_safe_path(cls, storage_key: str) -> str:
        """
        Resolves storage key to absolute path and strictly defends against path traversal.
        """
        upload_dir = os.path.abspath(settings.UPLOAD_DIR)

        # Explicitly reject directory traversal sequences and absolute paths
        if (
            ".." in storage_key
            or os.path.isabs(storage_key)
            or storage_key.startswith("/")
            or storage_key.startswith("\\")
        ):
            raise PathTraversalError(f"Path traversal detected: {storage_key}")

        clean_key = os.path.basename(storage_key)
        target_path = os.path.abspath(os.path.join(upload_dir, clean_key))

        if not target_path.startswith(upload_dir):
            raise PathTraversalError(f"Path traversal detected: {storage_key}")

        return target_path

    @classmethod
    def save_upload_stream(
        cls,
        stream: BinaryIO,
        original_filename: str,
        chunk_size: int = 65536,
    ) -> Tuple[str, str, int, str]:
        """
        Streams file to secure disk storage, computing SHA-256 hex digest incrementally.
        Guarantees zero orphaned files on failure or size limit breach.

        Returns:
            Tuple of (storage_key, file_fingerprint, total_bytes, detected_mime_type)
        """
        cls.ensure_upload_dir()
        random_filename = f"{uuid.uuid4().hex}.dat"
        target_path = cls.resolve_safe_path(random_filename)

        hasher = hashlib.sha256()
        total_bytes = 0
        first_chunk = True
        detected_mime = "text/csv"

        try:
            with open(target_path, "wb") as f:
                while True:
                    chunk = stream.read(chunk_size)
                    if not chunk:
                        break

                    # Magic bytes check on first chunk
                    if first_chunk:
                        first_chunk = False
                        if chunk.startswith(b"PK\x03\x04"):
                            detected_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        elif b"\x00" in chunk:
                            # Binary non-ZIP file
                            raise InvalidFileFormatError("Uploaded file contains binary control bytes and is not valid CSV or XLSX.")
                        else:
                            detected_mime = "text/csv"

                    total_bytes += len(chunk)
                    if total_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
                        raise FileSizeExceededError(
                            f"File size exceeds maximum allowed upload size of {settings.MAX_UPLOAD_SIZE_BYTES} bytes."
                        )

                    hasher.update(chunk)
                    f.write(chunk)

            # Restrict filesystem permissions on POSIX systems
            try:
                os.chmod(target_path, 0o600)
            except Exception:
                pass

            file_fingerprint = hasher.hexdigest()
            storage_key = f"uploads/{random_filename}"
            return storage_key, file_fingerprint, total_bytes, detected_mime

        except Exception:
            # Clean up partial file immediately to prevent orphaned disk residue
            if os.path.exists(target_path):
                try:
                    os.remove(target_path)
                except Exception:
                    pass
            raise

    @classmethod
    def verify_file_integrity(cls, storage_key: str, expected_fingerprint: str) -> bool:
        """
        Reads stored file and verifies SHA-256 matches expected fingerprint.
        """
        target_path = cls.resolve_safe_path(storage_key)
        if not os.path.exists(target_path):
            return False

        hasher = hashlib.sha256()
        with open(target_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)

        return hasher.hexdigest() == expected_fingerprint

    @classmethod
    def delete_file(cls, storage_key: str) -> bool:
        """Safely removes file from disk."""
        try:
            target_path = cls.resolve_safe_path(storage_key)
            if os.path.exists(target_path):
                os.remove(target_path)
                return True
            return False
        except Exception:
            return False
