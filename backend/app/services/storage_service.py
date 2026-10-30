"""Secure file storage, path sanitization, and MIME/magic validation."""

import logging
import os
import re
import shutil
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Optional, Set, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS: Set[str] = {".pdf", ".docx", ".txt", ".csv"}

# Map extensions to canonical MIME types
CANONICAL_MIMES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".csv": "text/csv",
}


class StorageError(Exception):
    """Base exception for storage errors."""
    pass


class InvalidFileTypeError(StorageError):
    """Raised when file extension or content signature is invalid."""
    pass


class FileSizeExceededError(StorageError):
    """Raised when uploaded file exceeds max configured limit."""
    pass


class StorageService:
    """Manages secure local file persistence in data/uploads/<document-id>/."""

    def __init__(self, base_upload_dir: Optional[Path] = None):
        self._upload_dir = base_upload_dir or settings.upload_dir_path
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    @property
    def upload_dir(self) -> Path:
        return self._upload_dir

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize an untrusted filename, stripping directory traversal and illegal characters.

        Args:
            filename: Raw user-provided filename.

        Returns:
            Safe base filename with preserved extension.
        """
        if not filename:
            return "unnamed_file"

        # Remove null bytes
        cleaned = filename.replace("\x00", "")

        # Extract only the basename (strips paths like /foo/bar or ..\..\foo)
        cleaned = os.path.basename(cleaned)
        cleaned = cleaned.replace("\\", "/").split("/")[-1]

        # Remove directory traversal patterns
        cleaned = re.sub(r"\.\.+", ".", cleaned)

        # Retain only safe alphanumeric characters, dots, underscores, hyphens
        safe_name = re.sub(r"[^\w\.\-]", "_", cleaned)
        safe_name = safe_name.strip("._ ")

        if not safe_name:
            return "uploaded_file"

        return safe_name

    def validate_file(
        self,
        filename: str,
        content_bytes: bytes,
        declared_content_type: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Validate filename extension, file size, and file content signatures.

        Args:
            filename: Original user filename.
            content_bytes: Raw binary content of the file.
            declared_content_type: Optional MIME type from HTTP header.

        Returns:
            Tuple of (sanitized_extension, validated_mime_type).

        Raises:
            FileSizeExceededError: If file exceeds maximum upload size.
            InvalidFileTypeError: If extension is unsupported or content is invalid.
        """
        # 1. Size check
        size = len(content_bytes)
        if size == 0:
            raise InvalidFileTypeError("Uploaded file is empty (0 bytes).")

        if size > settings.max_upload_size_bytes:
            limit_mb = settings.MAX_UPLOAD_SIZE_MB
            raise FileSizeExceededError(
                f"File size ({size / (1024 * 1024):.1f} MB) exceeds maximum allowed limit of {limit_mb} MB."
            )

        # 2. Extension check
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise InvalidFileTypeError(
                f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        # 3. Content signature (magic bytes) validation
        validated_mime = self._verify_content_signature(ext, content_bytes, declared_content_type)

        return ext.lstrip("."), validated_mime

    def _verify_content_signature(
        self,
        ext: str,
        data: bytes,
        declared_mime: Optional[str],
    ) -> str:
        """Verify binary signature against file extension."""
        if ext == ".pdf":
            # PDF header check: first bytes must contain %PDF
            if not data.startswith(b"%PDF"):
                raise InvalidFileTypeError("File has .pdf extension but is not a valid PDF document (missing %PDF signature).")
            return "application/pdf"

        elif ext == ".docx":
            # DOCX is a ZIP archive containing word/
            if not data.startswith(b"PK\x03\x04"):
                raise InvalidFileTypeError("File has .docx extension but is not a valid OpenXML document (missing ZIP header).")
            try:
                with zipfile.ZipFile(BytesIO(data)) as zf:
                    namelist = zf.namelist()
                    if not any(name.startswith("word/") or name == "[Content_Types].xml" for name in namelist):
                        raise InvalidFileTypeError("File is a ZIP archive but does not contain Microsoft Word document structures.")
            except zipfile.BadZipFile as exc:
                raise InvalidFileTypeError("File has .docx extension but contains corrupt or invalid ZIP data.") from exc
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        elif ext == ".txt":
            # Verify text is decodable
            try:
                data.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    data.decode("latin-1")
                except Exception as exc:
                    raise InvalidFileTypeError("File has .txt extension but could not be decoded as text.") from exc
            return "text/plain"

        elif ext == ".csv":
            # Verify text decodable
            try:
                data.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    data.decode("latin-1")
                except Exception as exc:
                    raise InvalidFileTypeError("File has .csv extension but could not be decoded as text.") from exc
            return "text/csv"

        return CANONICAL_MIMES.get(ext, "application/octet-stream")

    def save_file(
        self,
        document_id: str,
        original_filename: str,
        content_bytes: bytes,
    ) -> Tuple[Path, str]:
        """Save uploaded file bytes into data/uploads/<document-id>/<sanitized_filename>.

        Args:
            document_id: UUID of the document.
            original_filename: Original filename from the user.
            content_bytes: Binary payload.

        Returns:
            Tuple of (absolute_filesystem_path, relative_storage_path).
        """
        # Ensure document-specific directory exists
        doc_dir = self._upload_dir / document_id
        doc_dir.mkdir(parents=True, exist_ok=True)

        safe_filename = self.sanitize_filename(original_filename)
        dest_path = doc_dir / safe_filename

        dest_path.write_bytes(content_bytes)
        logger.info(f"Safely persisted {len(content_bytes)} bytes to {dest_path}")

        # Compute normalized relative storage path (e.g. data/uploads/<id>/filename)
        try:
            relative_path = str(dest_path.relative_to(self._upload_dir.parent.parent)).replace("\\", "/")
        except ValueError:
            relative_path = f"data/uploads/{document_id}/{safe_filename}"

        return dest_path, relative_path

    def get_document_file_path(self, document_id: str, storage_path: Optional[str]) -> Path:
        """Resolve and verify absolute file path for an existing document, preventing traversal.

        Args:
            document_id: UUID of the document.
            storage_path: Stored storage_path string.

        Returns:
            Verified absolute Path to the file on disk.

        Raises:
            StorageError: If path traverses outside the document folder or file does not exist.
        """
        doc_dir = (self._upload_dir / document_id).resolve()
        if not doc_dir.exists():
            raise StorageError(f"Document storage directory not found for ID: {document_id}")

        if storage_path:
            # Extract filename from stored path
            target_filename = Path(storage_path).name
            candidate_path = (doc_dir / target_filename).resolve()
        else:
            # Fallback: find first file inside doc_dir
            files = [f for f in doc_dir.iterdir() if f.is_file()]
            if not files:
                raise StorageError(f"No stored files found in document directory: {document_id}")
            candidate_path = files[0].resolve()

        # Strict path traversal check
        if not candidate_path.is_relative_to(doc_dir):
            logger.critical(f"Path traversal attempt detected for document {document_id}: {candidate_path}")
            raise StorageError("Path traversal violation: file location is outside permitted boundaries.")

        if not candidate_path.is_file():
            raise StorageError(f"Stored file does not exist on disk: {candidate_path}")

        return candidate_path

    def delete_document_files(self, document_id: str) -> None:
        """Delete document folder and all its contents from disk."""
        doc_dir = (self._upload_dir / document_id).resolve()
        if doc_dir.exists() and doc_dir.is_relative_to(self._upload_dir.resolve()):
            try:
                shutil.rmtree(doc_dir)
                logger.info(f"Cleaned up storage directory for document: {document_id}")
            except Exception as exc:
                logger.warning(f"Could not remove directory {doc_dir}: {exc}")


storage_service = StorageService()
