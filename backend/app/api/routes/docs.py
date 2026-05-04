"""Document management routes."""
import io
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.db.models import User, Doc

router = APIRouter()

ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
    "text/markdown": "md",
    "text/csv": "csv",
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def _extract_text(data: bytes, content_type: str) -> str:
    """Extract plain text from uploaded file bytes."""
    if content_type == "text/plain" or content_type == "text/markdown" or content_type == "text/csv":
        return data.decode("utf-8", errors="replace")

    if content_type == "application/pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(data))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            return f"[PDF text extraction failed: {e}]"

    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        try:
            import docx
            doc = docx.Document(io.BytesIO(data))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as e:
            return f"[DOCX text extraction failed: {e}]"

    return "[Unsupported file type]"


class DocOut(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    created_at: str
    preview: str


@router.post("/upload", response_model=DocOut)
async def upload_doc(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'. Allowed: PDF, DOCX, TXT, MD, CSV"
        )

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5 MB.")

    text = _extract_text(data, file.content_type)

    doc = Doc(
        owner_id=str(current_user.id),
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=len(data),
        text_content=text,
    )
    await doc.insert()

    return DocOut(
        id=str(doc.id),
        filename=doc.filename,
        content_type=doc.content_type,
        size_bytes=doc.size_bytes,
        created_at=doc.created_at.strftime("%Y-%m-%d %H:%M"),
        preview=text[:200].replace("\n", " "),
    )


@router.get("/", response_model=List[DocOut])
async def list_docs(current_user: User = Depends(get_current_user)):
    # Superadmin/admin see all; regular users see only their own
    from app.db.models import UserRole
    if current_user.role in (UserRole.superadmin, UserRole.admin):
        docs = await Doc.find_all().to_list()
    else:
        docs = await Doc.find(Doc.owner_id == str(current_user.id)).to_list()

    return [
        DocOut(
            id=str(d.id),
            filename=d.filename,
            content_type=d.content_type,
            size_bytes=d.size_bytes,
            created_at=d.created_at.strftime("%Y-%m-%d %H:%M"),
            preview=d.text_content[:200].replace("\n", " "),
        )
        for d in docs
    ]


@router.delete("/{doc_id}")
async def delete_doc(doc_id: str, current_user: User = Depends(get_current_user)):
    from beanie import PydanticObjectId
    from app.db.models import UserRole
    doc = await Doc.get(PydanticObjectId(doc_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Only owner or admin/superadmin can delete
    if doc.owner_id != str(current_user.id) and current_user.role not in (UserRole.superadmin, UserRole.admin):
        raise HTTPException(status_code=403, detail="Not authorised to delete this document")

    await doc.delete()
    return {"deleted": doc_id}
