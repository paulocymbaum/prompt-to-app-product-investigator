"""
Export API Routes - REST endpoints for investigation report export.

Provides API endpoints for exporting investigation reports in multiple
formats: PDF, HTML, and Markdown. Supports single export and batch operations.

Endpoints:
- GET /api/export/pdf/{session_id} - Export as PDF
- GET /api/export/markdown/{session_id} - Export as Markdown
- GET /api/export/html/{session_id} - Export as HTML
- POST /api/export/batch - Batch export multiple sessions
"""

from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Literal
from datetime import datetime
from io import BytesIO
import structlog

from storage.conversation_storage import ConversationStorage
from services.prompt_generator import PromptGenerator
from services.graph_service import GraphService
from services.export_service import ExportService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/export", tags=["export"])


# Request/Response Models
class BatchExportRequest(BaseModel):
    """Request model for batch export."""
    session_ids: List[str]
    format: Literal["pdf", "markdown", "html"]


class ExportResponse(BaseModel):
    """Response model for export operations."""
    session_id: str
    format: str
    filename: str
    size_bytes: int
    generated_at: str


class BatchExportResponse(BaseModel):
    """Response model for batch export."""
    total: int
    successful: int
    failed: int
    exports: List[ExportResponse]
    errors: List[dict]


# Dependency Injection
def get_export_service() -> ExportService:
    """
    Dependency injection for ExportService.
    
    Creates ExportService with all required dependencies.
    """
    storage = ConversationStorage()
    prompt_gen = PromptGenerator(storage)
    graph_service = GraphService(storage)
    return ExportService(storage, prompt_gen, graph_service)


# Endpoints
@router.get(
    "/pdf/{session_id}",
    response_class=Response,
    summary="Export investigation as PDF",
    description="Generate and download a PDF report of the investigation session"
)
async def export_pdf(
    session_id: str,
    service: ExportService = Depends(get_export_service)
):
    """
    Export investigation report as PDF.
    
    Generates a professionally formatted PDF document containing:
    - Full conversation history
    - Embedded conversation graph
    - Generated development prompt
    - Session metadata
    
    Args:
        session_id: Unique session identifier
        service: ExportService instance (injected)
        
    Returns:
        PDF file as application/pdf
        
    Raises:
        404: Session not found
        500: PDF generation failed
    """
    logger.info("PDF export requested", session_id=session_id)
    
    try:
        pdf_bytes = await service.export_to_pdf(session_id)
        
        filename = f"investigation_report_{session_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        logger.info(
            "PDF export successful",
            session_id=session_id,
            filename=filename,
            size_bytes=len(pdf_bytes)
        )
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes))
            }
        )
        
    except ValueError as e:
        if "not found" in str(e):
            logger.warning("PDF export failed - session not found", session_id=session_id)
            raise HTTPException(status_code=404, detail=str(e))
        else:
            logger.error("PDF export failed", session_id=session_id, error=str(e))
            raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
    except Exception as e:
        logger.error("PDF export exception", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/markdown/{session_id}",
    response_class=Response,
    summary="Export investigation as Markdown",
    description="Generate and download a Markdown report of the investigation session"
)
async def export_markdown(
    session_id: str,
    service: ExportService = Depends(get_export_service)
):
    """
    Export investigation report as Markdown.
    
    Generates a Markdown document containing:
    - Full conversation history
    - Mermaid diagram code
    - Generated development prompt
    - Session metadata
    
    Args:
        session_id: Unique session identifier
        service: ExportService instance (injected)
        
    Returns:
        Markdown file as text/markdown
        
    Raises:
        404: Session not found
        500: Markdown generation failed
    """
    logger.info("Markdown export requested", session_id=session_id)
    
    try:
        markdown_content = await service.export_to_markdown(session_id)
        
        filename = f"investigation_report_{session_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
        
        logger.info(
            "Markdown export successful",
            session_id=session_id,
            filename=filename,
            size_chars=len(markdown_content)
        )
        
        return Response(
            content=markdown_content.encode('utf-8'),
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(markdown_content.encode('utf-8')))
            }
        )
        
    except ValueError as e:
        if "not found" in str(e):
            logger.warning("Markdown export failed - session not found", session_id=session_id)
            raise HTTPException(status_code=404, detail=str(e))
        else:
            logger.error("Markdown export failed", session_id=session_id, error=str(e))
            raise HTTPException(status_code=500, detail=f"Markdown generation failed: {str(e)}")
    except Exception as e:
        logger.error("Markdown export exception", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/html/{session_id}",
    response_class=HTMLResponse,
    summary="Export investigation as HTML",
    description="Generate and display/download an HTML report of the investigation session"
)
async def export_html(
    session_id: str,
    download: bool = True,
    service: ExportService = Depends(get_export_service)
):
    """
    Export investigation report as HTML.
    
    Generates an HTML document containing:
    - Full conversation history
    - Embedded Mermaid graph (rendered client-side)
    - Generated development prompt
    - Session metadata
    - Professional styling
    
    Args:
        session_id: Unique session identifier
        download: If True, forces download; if False, displays in browser
        service: ExportService instance (injected)
        
    Returns:
        HTML file as text/html
        
    Raises:
        404: Session not found
        500: HTML generation failed
    """
    logger.info("HTML export requested", session_id=session_id, download=download)
    
    try:
        html_content = await service.export_to_html(session_id)
        
        filename = f"investigation_report_{session_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.html"
        
        logger.info(
            "HTML export successful",
            session_id=session_id,
            filename=filename,
            size_chars=len(html_content)
        )
        
        headers = {
            "Content-Length": str(len(html_content.encode('utf-8')))
        }
        
        if download:
            headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        
        return HTMLResponse(
            content=html_content,
            headers=headers
        )
        
    except ValueError as e:
        if "not found" in str(e):
            logger.warning("HTML export failed - session not found", session_id=session_id)
            raise HTTPException(status_code=404, detail=str(e))
        else:
            logger.error("HTML export failed", session_id=session_id, error=str(e))
            raise HTTPException(status_code=500, detail=f"HTML generation failed: {str(e)}")
    except Exception as e:
        logger.error("HTML export exception", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/batch",
    response_model=BatchExportResponse,
    summary="Batch export multiple sessions",
    description="Export multiple investigation sessions in a single request"
)
async def export_batch(
    request: BatchExportRequest,
    service: ExportService = Depends(get_export_service)
):
    """
    Batch export multiple investigation sessions.
    
    Exports multiple sessions in the specified format. Returns summary
    of successful and failed exports.
    
    Args:
        request: BatchExportRequest with session_ids and format
        service: ExportService instance (injected)
        
    Returns:
        BatchExportResponse with export results and errors
        
    Raises:
        400: Invalid format specified
        500: Batch export failed
    """
    logger.info(
        "Batch export requested",
        session_count=len(request.session_ids),
        format=request.format
    )
    
    exports = []
    errors = []
    successful = 0
    failed = 0
    
    for session_id in request.session_ids:
        try:
            # Export based on format
            if request.format == "pdf":
                content = await service.export_to_pdf(session_id)
                size_bytes = len(content)
            elif request.format == "markdown":
                content = await service.export_to_markdown(session_id)
                size_bytes = len(content.encode('utf-8'))
            elif request.format == "html":
                content = await service.export_to_html(session_id)
                size_bytes = len(content.encode('utf-8'))
            else:
                raise ValueError(f"Invalid format: {request.format}")
            
            filename = f"investigation_report_{session_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{request.format}"
            
            exports.append(ExportResponse(
                session_id=session_id,
                format=request.format,
                filename=filename,
                size_bytes=size_bytes,
                generated_at=datetime.utcnow().isoformat()
            ))
            
            successful += 1
            
            logger.info(
                "Batch export item successful",
                session_id=session_id,
                format=request.format
            )
            
        except Exception as e:
            failed += 1
            errors.append({
                "session_id": session_id,
                "error": str(e)
            })
            
            logger.error(
                "Batch export item failed",
                session_id=session_id,
                error=str(e)
            )
    
    logger.info(
        "Batch export completed",
        total=len(request.session_ids),
        successful=successful,
        failed=failed
    )
    
    return BatchExportResponse(
        total=len(request.session_ids),
        successful=successful,
        failed=failed,
        exports=exports,
        errors=errors
    )
