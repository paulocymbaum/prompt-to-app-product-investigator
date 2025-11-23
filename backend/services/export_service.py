"""
Export Service - Generate investigation reports in multiple formats.

This service provides export functionality for investigation reports in PDF, HTML,
and Markdown formats. It integrates with ConversationStorage, PromptGenerator,
and GraphService to create comprehensive reports.

Dependencies:
- weasyprint: PDF generation
- markdown: HTML conversion
- jinja2: Template rendering
"""

from datetime import datetime
from typing import Dict, List, Optional
import markdown as md
from jinja2 import Template
import structlog

from storage.conversation_storage import ConversationStorage
from services.prompt_generator import PromptGenerator
from services.graph_service import GraphService

# Optional WeasyPrint import - gracefully handle if not available
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as e:
    WEASYPRINT_AVAILABLE = False
    WEASYPRINT_ERROR = str(e)

logger = structlog.get_logger(__name__)


class ExportService:
    """
    Service for exporting investigation reports in multiple formats.
    
    Provides methods to export conversation history, generated prompts,
    and visualization graphs in PDF, HTML, and Markdown formats.
    """
    
    def __init__(
        self,
        storage: ConversationStorage,
        prompt_gen: PromptGenerator,
        graph_service: GraphService
    ):
        """
        Initialize ExportService with required dependencies.
        
        Args:
            storage: ConversationStorage for loading conversation data
            prompt_gen: PromptGenerator for generating prompts
            graph_service: GraphService for graph data and visualization
        """
        self.storage = storage
        self.prompt_gen = prompt_gen
        self.graph_service = graph_service
        self.logger = logger.bind(service="export")
    
    async def export_to_pdf(self, session_id: str) -> bytes:
        """
        Export investigation report to PDF format.
        
        Generates HTML content first, then converts to PDF using weasyprint.
        Includes full Q&A history, embedded graph, and generated prompt.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            bytes: PDF file content
            
        Raises:
            ValueError: If session not found or conversion fails or WeasyPrint not available
        """
        self.logger.info("Exporting to PDF", session_id=session_id)
        
        # Check if WeasyPrint is available
        if not WEASYPRINT_AVAILABLE:
            error_msg = f"PDF export not available: WeasyPrint dependencies missing. Install system dependencies (pango, gdk-pixbuf, etc.). Error: {WEASYPRINT_ERROR}"
            self.logger.error("PDF export unavailable", error=error_msg)
            raise ValueError(error_msg)
        
        try:
            # Generate HTML first
            html_content = await self.export_to_html(session_id)
            
            # Convert to PDF
            pdf_bytes = HTML(string=html_content).write_pdf()
            
            if pdf_bytes is None:
                raise ValueError("PDF generation returned None")
            
            self.logger.info(
                "PDF export successful",
                session_id=session_id,
                size_bytes=len(pdf_bytes)
            )
            
            return pdf_bytes
            
        except Exception as e:
            self.logger.error(
                "PDF export failed",
                session_id=session_id,
                error=str(e)
            )
            raise ValueError(f"Failed to generate PDF: {str(e)}")
    
    async def export_to_html(self, session_id: str) -> str:
        """
        Export investigation report to HTML format.
        
        Generates a complete HTML document with embedded Mermaid graph,
        full conversation history, and generated prompt. Includes
        professional styling and JavaScript for graph rendering.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            str: HTML content
            
        Raises:
            ValueError: If session not found
        """
        self.logger.info("Exporting to HTML", session_id=session_id)
        
        try:
            # Load all required data
            conversation = await self.storage.load_conversation(session_id)
            
            if not conversation:
                raise ValueError(f"Session {session_id} not found")
            
            chunks = self.storage.parse_chunks(conversation)
            prompt = await self.prompt_gen.generate_prompt(session_id)
            graph_data = await self.graph_service.build_graph(session_id)
            mermaid = self.graph_service.export_mermaid(graph_data)
            
            # Extract metadata
            metadata = graph_data.get('metadata', {})
            created_at = metadata.get('created_at', 'N/A')
            if isinstance(created_at, datetime):
                created_at = created_at.strftime('%Y-%m-%d %H:%M:%S')
            duration = metadata.get('duration_minutes', 0)
            total_interactions = metadata.get('total_interactions', len(chunks))
            
            # Build HTML using template
            html_template = Template(self._get_html_template())
            html_content = html_template.render(
                session_id=session_id,
                created_at=created_at,
                duration_minutes=duration,
                total_interactions=total_interactions,
                interactions=[self._format_interaction_html(chunk) for chunk in chunks],
                mermaid_graph=mermaid,
                prompt_html=md.markdown(
                    prompt,
                    extensions=['fenced_code', 'tables', 'nl2br']
                ),
                report_date=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            )
            
            self.logger.info(
                "HTML export successful",
                session_id=session_id,
                size_chars=len(html_content),
                interactions=total_interactions
            )
            
            return html_content
            
        except ValueError:
            raise
        except Exception as e:
            self.logger.error(
                "HTML export failed",
                session_id=session_id,
                error=str(e)
            )
            raise ValueError(f"Failed to generate HTML: {str(e)}")
    
    async def export_to_markdown(self, session_id: str) -> str:
        """
        Export investigation report to Markdown format.
        
        Generates a markdown document with full conversation history
        and generated prompt. Suitable for version control and
        plain text documentation.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            str: Markdown content
            
        Raises:
            ValueError: If session not found
        """
        self.logger.info("Exporting to Markdown", session_id=session_id)
        
        try:
            # Load data
            conversation = await self.storage.load_conversation(session_id)
            
            if not conversation:
                raise ValueError(f"Session {session_id} not found")
            
            prompt = await self.prompt_gen.generate_prompt(session_id)
            graph_data = await self.graph_service.build_graph(session_id)
            
            # Extract metadata
            metadata = graph_data.get('metadata', {})
            created_at = metadata.get('created_at', 'N/A')
            if isinstance(created_at, datetime):
                created_at = created_at.strftime('%Y-%m-%d %H:%M:%S')
            duration = metadata.get('duration_minutes', 0)
            
            # Parse chunks for better formatting
            chunks = self.storage.parse_chunks(conversation)
            formatted_interactions = '\n\n'.join([
                self._format_interaction_markdown(chunk) for chunk in chunks
            ])
            
            # Build markdown
            markdown_content = f"""# Product Investigation Report

**Session ID:** `{session_id}`  
**Date:** {created_at}  
**Duration:** {duration} minutes  
**Report Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

---

## Conversation History

{formatted_interactions}

---

## Conversation Flow

The following Mermaid diagram shows the conversation flow:

```mermaid
{self.graph_service.export_mermaid(graph_data)}
```

---

## Generated Development Prompt

{prompt}

---

## Export Information

This report was automatically generated from session `{session_id}`.  
Total interactions: {len(chunks)}

"""
            
            self.logger.info(
                "Markdown export successful",
                session_id=session_id,
                size_chars=len(markdown_content),
                interactions=len(chunks)
            )
            
            return markdown_content
            
        except ValueError:
            raise
        except Exception as e:
            self.logger.error(
                "Markdown export failed",
                session_id=session_id,
                error=str(e)
            )
            raise ValueError(f"Failed to generate Markdown: {str(e)}")
    
    def _format_interaction_html(self, chunk: str) -> Dict[str, str]:
        """
        Format single interaction chunk as structured HTML data.
        
        Args:
            chunk: Raw conversation chunk
            
        Returns:
            Dict with question and answer
        """
        lines = chunk.split('\n')
        question = ''
        answer = ''
        
        for line in lines:
            if '**Question:**' in line:
                question = line.split('**Question:**')[1].strip()
            elif '**Answer:**' in line:
                answer = line.split('**Answer:**')[1].strip()
        
        # If question/answer format not found, try alternative formats
        if not question and not answer:
            # Try to extract from plain format
            content_lines = [l for l in lines if l.strip()]
            if len(content_lines) >= 2:
                question = content_lines[0]
                answer = '\n'.join(content_lines[1:])
            elif len(content_lines) == 1:
                answer = content_lines[0]
        
        return {
            'question': question or 'N/A',
            'answer': answer or 'N/A'
        }
    
    def _format_interaction_markdown(self, chunk: str) -> str:
        """
        Format single interaction chunk as Markdown.
        
        Args:
            chunk: Raw conversation chunk
            
        Returns:
            Formatted markdown string
        """
        lines = chunk.split('\n')
        question = ''
        answer = ''
        
        for line in lines:
            if '**Question:**' in line:
                question = line.split('**Question:**')[1].strip()
            elif '**Answer:**' in line:
                answer = line.split('**Answer:**')[1].strip()
        
        # If question/answer format not found, return as-is
        if not question and not answer:
            return chunk
        
        return f"""### Q: {question}

**A:** {answer}"""
    
    def _get_html_template(self) -> str:
        """
        Get HTML template for report generation.
        
        Returns:
            HTML template string with Jinja2 placeholders
        """
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Product Investigation Report - {{ session_id }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #fff;
            padding: 40px;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        h1 {
            color: #1a1a1a;
            font-size: 2.5em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #2563EB;
        }
        
        h2 {
            color: #2563EB;
            font-size: 1.8em;
            margin-top: 40px;
            margin-bottom: 20px;
        }
        
        .metadata {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            border-left: 4px solid #2563EB;
        }
        
        .metadata p {
            margin: 5px 0;
            font-size: 0.95em;
        }
        
        .metadata strong {
            color: #1a1a1a;
            min-width: 150px;
            display: inline-block;
        }
        
        .interaction {
            margin: 20px 0;
            padding: 20px;
            background: #f5f5f5;
            border-radius: 8px;
            border-left: 4px solid #10b981;
        }
        
        .question {
            font-weight: 600;
            color: #2563EB;
            font-size: 1.1em;
            margin-bottom: 10px;
        }
        
        .answer {
            color: #4b5563;
            padding-left: 20px;
            line-height: 1.8;
        }
        
        .prompt {
            margin-top: 40px;
            padding: 25px;
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .prompt pre {
            background: #282c34;
            color: #abb2bf;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }
        
        .prompt code {
            font-family: 'Courier New', monospace;
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
        }
        
        .prompt pre code {
            background: transparent;
            padding: 0;
        }
        
        .mermaid-container {
            margin: 30px 0;
            padding: 20px;
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            text-align: center;
        }
        
        footer {
            margin-top: 60px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            text-align: center;
            color: #6b7280;
            font-size: 0.9em;
        }
        
        @media print {
            body {
                padding: 20px;
            }
            
            .interaction {
                page-break-inside: avoid;
            }
        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
</head>
<body>
    <h1>Product Investigation Report</h1>
    
    <div class="metadata">
        <p><strong>Session ID:</strong> {{ session_id }}</p>
        <p><strong>Created:</strong> {{ created_at }}</p>
        <p><strong>Duration:</strong> {{ duration_minutes }} minutes</p>
        <p><strong>Total Interactions:</strong> {{ total_interactions }}</p>
        <p><strong>Report Generated:</strong> {{ report_date }} UTC</p>
    </div>
    
    <h2>Conversation History</h2>
    {% for interaction in interactions %}
    <div class="interaction">
        <div class="question">Q: {{ interaction.question }}</div>
        <div class="answer">A: {{ interaction.answer }}</div>
    </div>
    {% endfor %}
    
    <h2>Conversation Flow</h2>
    <div class="mermaid-container">
        <div class="mermaid">
{{ mermaid_graph }}
        </div>
    </div>
    
    <h2>Generated Development Prompt</h2>
    <div class="prompt">
        {{ prompt_html|safe }}
    </div>
    
    <footer>
        <p>This report was automatically generated from session <strong>{{ session_id }}</strong></p>
        <p>Product Investigation System - AI-Powered Development Planning</p>
    </footer>
    
    <script>
        mermaid.initialize({ 
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose'
        });
    </script>
</body>
</html>"""
