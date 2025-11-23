#!/bin/bash

# TASK-3.1: Implement Prompt Generator Service
# This script creates the prompt generator service with comprehensive prompt generation
# Following SOLID principles and DRY concepts

set -e

echo "=== TASK-3.1: Creating Prompt Generator Service ==="

# Create the prompt generator service
cat > backend/services/prompt_generator.py << 'PYTHON_CODE'
"""
Prompt Generator Service

This service generates comprehensive, best-practice prompts from investigation data.
Follows SOLID principles:
- Single Responsibility: Only generates prompts
- Open/Closed: Extensible through template customization
- Dependency Inversion: Depends on storage abstraction
"""

from typing import Dict, List, Optional
from jinja2 import Template
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PromptGenerator:
    """
    Generate comprehensive development prompts from investigation data.
    
    Responsibilities:
    - Aggregate investigation answers by category
    - Structure prompts using best practices
    - Include SOLID and DRY requirements
    - Suggest architecture patterns
    - Validate and optimize prompts
    """
    
    def __init__(self, storage):
        """
        Initialize prompt generator.
        
        Args:
            storage: ConversationStorage instance for loading conversation history
        """
        self.storage = storage
        self.template = self._load_template()
    
    def _load_template(self) -> Template:
        """Load Jinja2 template for prompt generation."""
        template_str = """# Product Development Prompt

## Your Role
You are an expert software architect and full-stack developer with deep expertise in:
- Software design patterns and architecture
- SOLID principles and clean code practices
- Modern web development frameworks
- Database design and optimization
- User experience and interface design

## Product Context

### Product Overview
{{ product_overview }}

### Core Functionality
{{ functionality }}

### Target Users
{{ users }}
{% if demographics %}
- **Demographics:** {{ demographics }}
{% endif %}
{% if technical_level %}
- **Technical Level:** {{ technical_level }}
{% endif %}
{% if use_case %}
- **Primary Use Case:** {{ use_case }}
{% endif %}

### Design Requirements
{{ design_requirements }}

### Market Context
{% if market_segment %}
- **Target Market:** {{ market_segment }}
{% endif %}
{% if competitors %}
- **Competitors:** {{ competitors }}
{% endif %}
{% if value_proposition %}
- **Unique Value Proposition:** {{ value_proposition }}
{% endif %}

### Technical Requirements
{{ technical_requirements }}

## Development Principles

### SOLID Principles (MANDATORY)
You MUST apply these principles rigorously:

1. **Single Responsibility Principle (SRP)**
   - Each class/module has ONE reason to change
   - Separate concerns into distinct, focused components
   
2. **Open/Closed Principle (OCP)**
   - Open for extension, closed for modification
   - Use interfaces, abstract classes, and dependency injection
   
3. **Liskov Substitution Principle (LSP)**
   - Derived classes must be substitutable for base classes
   - Maintain behavioral compatibility in inheritance
   
4. **Interface Segregation Principle (ISP)**
   - Many specific interfaces > one general interface
   - Clients shouldn't depend on unused methods
   
5. **Dependency Inversion Principle (DIP)**
   - Depend on abstractions, not concretions
   - High-level modules independent of low-level modules

### DRY (Don't Repeat Yourself)
- **NO code duplication** - extract reusable functions/components
- **Create utility libraries** for common operations
- **Use composition** over copy-paste
- **Centralize configuration** and constants
- **Single source of truth** for business logic

### Code Organization
- **Modular architecture** with clear separation of concerns
- **Consistent naming conventions** across the codebase
- **Comprehensive documentation** for public APIs
- **Type safety** using TypeScript/Python type hints
- **Error handling** at appropriate boundaries

## Architecture Recommendations

{{ architecture_pattern }}

### Suggested Tech Stack
{{ tech_stack }}

### Folder Structure
{{ folder_structure }}

## Functional Requirements

{{ functional_requirements }}

## Non-Functional Requirements

### Performance
- Page load time < 3 seconds
- API response time < 500ms (95th percentile)
- Smooth animations (60 FPS)

### Security
- Input validation and sanitization
- Authentication and authorization
- Protection against common vulnerabilities (XSS, CSRF, SQL injection)
- Secure data transmission (HTTPS)

### Maintainability
- Unit test coverage > 80%
- Integration tests for critical paths
- Clear README with setup instructions
- API documentation (OpenAPI/Swagger)
- Code comments for complex logic

### Scalability
- Design for horizontal scaling
- Efficient database queries
- Caching strategy for frequent operations
- Async processing for long-running tasks

## Output Format

Please provide:

1. **High-level architecture diagram** (text-based or Mermaid)
2. **Database schema** with relationships
3. **API endpoint specifications**
4. **Component hierarchy** (for frontend)
5. **Key code snippets** demonstrating:
   - SOLID principles in action
   - DRY implementation examples
   - Core business logic
   - Authentication flow
   - Data access layer
6. **Setup instructions** for development environment
7. **Testing strategy** overview

## Constraints

{{ constraints }}

## Additional Context

{{ additional_context }}

---

**Remember:** Prioritize clean, maintainable code over clever solutions. Future developers (including yourself) should be able to understand and extend this codebase easily.
"""
        return Template(template_str)
    
    async def generate_prompt(self, session_id: str) -> str:
        """
        Generate comprehensive prompt from session data.
        
        Args:
            session_id: Session ID to generate prompt for
            
        Returns:
            Complete formatted prompt string
            
        Raises:
            ValueError: If prompt generation fails or is incomplete
        """
        logger.info(f"Generating prompt for session {session_id}")
        
        try:
            # Load conversation history
            conversation = await self.storage.load_conversation(session_id)
            chunks = self.storage.parse_chunks(conversation)
            
            # Extract answers by category
            answers = self._extract_answers_by_category(chunks)
            
            # Determine architecture pattern
            architecture = self._suggest_architecture(answers)
            
            # Determine tech stack
            tech_stack = self._suggest_tech_stack(answers)
            
            # Build folder structure
            folder_structure = self._generate_folder_structure(answers, tech_stack)
            
            # Generate functional requirements
            functional_reqs = self._generate_functional_requirements(answers)
            
            # Compile template data
            template_data = {
                'product_overview': self._get_answer_value(answers, 'functionality', 'overview', 
                                                          'A software product'),
                'functionality': self._format_functionality(answers),
                'users': self._format_users(answers),
                'demographics': self._get_answer_value(answers, 'demographics', 'summary', ''),
                'technical_level': self._get_answer_value(answers, 'users', 'technical_level', 'intermediate'),
                'use_case': self._get_answer_value(answers, 'users', 'primary_use_case', ''),
                'design_requirements': self._format_design(answers),
                'market_segment': self._get_answer_value(answers, 'market', 'segment', ''),
                'competitors': self._get_answer_value(answers, 'market', 'competitors', ''),
                'value_proposition': self._get_answer_value(answers, 'market', 'value_prop', ''),
                'technical_requirements': self._format_technical(answers),
                'architecture_pattern': architecture,
                'tech_stack': tech_stack,
                'folder_structure': folder_structure,
                'functional_requirements': functional_reqs,
                'constraints': self._get_answer_value(answers, 'technical', 'constraints', 'None specified'),
                'additional_context': self._compile_additional_context(answers)
            }
            
            # Render prompt
            prompt = self.template.render(**template_data)
            
            # Validate and optimize
            if not self._validate_prompt(prompt):
                raise ValueError("Generated prompt incomplete or invalid")
            
            prompt = self._optimize_token_count(prompt)
            
            logger.info(f"Successfully generated prompt ({len(prompt)} characters)")
            return prompt
            
        except Exception as e:
            logger.error(f"Failed to generate prompt: {str(e)}")
            raise
    
    def _extract_answers_by_category(self, chunks: List[str]) -> Dict:
        """
        Parse chunks and organize answers by category.
        
        Args:
            chunks: List of conversation chunks
            
        Returns:
            Dictionary organized by category
        """
        answers = {
            'functionality': {},
            'users': {},
            'demographics': {},
            'design': {},
            'market': {},
            'technical': {}
        }
        
        for chunk in chunks:
            # Extract Q&A from chunk
            lines = chunk.split('\n')
            question = ''
            answer = ''
            
            for line in lines:
                if '**Question:**' in line:
                    question = line.replace('**Question:**', '').strip()
                elif '**Answer:**' in line:
                    answer = line.replace('**Answer:**', '').strip()
            
            if not question or not answer:
                continue
                
            # Categorize based on question content
            category = self._categorize_question(question)
            if category:
                key = self._extract_key_from_question(question)
                answers[category][key] = answer
        
        return answers
    
    def _categorize_question(self, question: str) -> Optional[str]:
        """Determine category from question text."""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['functionality', 'feature', 'does', 'purpose', 'solve']):
            return 'functionality'
        elif any(word in question_lower for word in ['user', 'audience', 'who will', 'customer']):
            return 'users'
        elif any(word in question_lower for word in ['age', 'demographic', 'location', 'geographic']):
            return 'demographics'
        elif any(word in question_lower for word in ['design', 'style', 'color', 'ui', 'ux', 'interface']):
            return 'design'
        elif any(word in question_lower for word in ['market', 'competitor', 'business model', 'revenue']):
            return 'market'
        elif any(word in question_lower for word in ['technical', 'technology', 'stack', 'performance', 'platform']):
            return 'technical'
        
        return None
    
    def _suggest_architecture(self, answers: Dict) -> str:
        """Suggest architecture pattern based on product complexity."""
        functionality = answers.get('functionality', {})
        technical = answers.get('technical', {})
        
        # Analyze product type from answers
        all_text = ' '.join(str(v) for v in functionality.values())
        tech_text = ' '.join(str(v) for v in technical.values())
        combined = (all_text + ' ' + tech_text).lower()
        
        is_web_app = any(word in combined for word in ['web', 'website', 'browser', 'online'])
        is_mobile = any(word in combined for word in ['mobile', 'ios', 'android', 'app store'])
        has_realtime = any(word in combined for word in ['realtime', 'real-time', 'chat', 'live', 'websocket'])
        is_api = any(word in combined for word in ['api', 'backend', 'service', 'microservice'])
        
        architecture = "### Recommended Architecture Pattern\n\n"
        
        if has_realtime:
            architecture += """**Event-Driven Architecture with WebSockets**

- **Frontend:** React with WebSocket client
- **Backend:** FastAPI with WebSocket support or Node.js + Socket.io
- **Message Queue:** Redis Pub/Sub or RabbitMQ
- **Database:** PostgreSQL + Redis for real-time data

**Rationale:** Handles real-time communication efficiently, scalable for concurrent connections.
"""
        elif is_mobile and is_web_app:
            architecture += """**Cross-Platform Architecture**

- **Frontend:** React Native (mobile) + React Web (web) with shared business logic
- **Backend:** RESTful API (FastAPI or Express)
- **State Management:** Redux with shared reducers
- **Database:** PostgreSQL with JSON support

**Rationale:** Maximum code reuse between platforms, single backend for all clients.
"""
        elif is_mobile:
            architecture += """**Mobile-First Architecture**

- **Framework:** React Native or Flutter
- **State Management:** Redux/MobX or Provider/Riverpod
- **API Layer:** RESTful or GraphQL
- **Offline Support:** SQLite + sync mechanism
- **Backend:** Node.js/FastAPI with mobile-optimized endpoints

**Rationale:** Native performance, offline-first capability, app store distribution.
"""
        elif is_api:
            architecture += """**Microservices Architecture**

- **API Gateway:** Kong or AWS API Gateway
- **Services:** Independent microservices with clear boundaries
- **Communication:** RESTful + Message Queue (RabbitMQ/Kafka)
- **Database:** Per-service databases (Postgres, MongoDB, Redis)
- **Orchestration:** Docker + Kubernetes

**Rationale:** Scalable, independent deployments, technology flexibility.
"""
        elif is_web_app:
            architecture += """**MVC (Model-View-Controller) / MVVM (Model-View-ViewModel)**

- **Frontend:** React/Vue with component-based architecture
- **Backend:** RESTful API (FastAPI/Express)
- **Database:** PostgreSQL or MongoDB
- **State Management:** Redux/Vuex/Context API
- **Caching:** Redis for session and frequently accessed data

**Rationale:** Clean separation of concerns, testable, maintainable, proven pattern.
"""
        else:
            architecture += """**Layered Architecture**

- **Presentation Layer:** Frontend framework (React/Vue)
- **Business Logic Layer:** Service classes with SOLID principles
- **Data Access Layer:** Repository pattern
- **Database Layer:** Relational (PostgreSQL) or NoSQL (MongoDB)

**Rationale:** Clear separation, easy to test and maintain, flexible for future changes.
"""
        
        return architecture
    
    def _suggest_tech_stack(self, answers: Dict) -> str:
        """Suggest technology stack based on requirements."""
        technical = answers.get('technical', {})
        functionality = answers.get('functionality', {})
        
        # Extract preferences
        preferences = ' '.join(str(v) for v in list(technical.values()) + list(functionality.values())).lower()
        
        stack = "### Suggested Technology Stack\n\n"
        
        # Frontend
        if 'react' in preferences:
            stack += "**Frontend:** React 18+ with TypeScript\n"
        elif 'vue' in preferences:
            stack += "**Frontend:** Vue 3 with TypeScript\n"
        elif 'angular' in preferences:
            stack += "**Frontend:** Angular with TypeScript\n"
        else:
            stack += "**Frontend:** React 18+ with TypeScript (recommended for ecosystem and community)\n"
        
        # Backend
        if 'python' in preferences or 'fastapi' in preferences:
            stack += "**Backend:** Python 3.10+ with FastAPI\n"
        elif 'node' in preferences or 'javascript' in preferences or 'express' in preferences:
            stack += "**Backend:** Node.js 18+ with Express or NestJS\n"
        elif 'django' in preferences:
            stack += "**Backend:** Python with Django REST Framework\n"
        else:
            stack += "**Backend:** Python 3.10+ with FastAPI (recommended for performance and async support)\n"
        
        # Database
        if 'nosql' in preferences or 'mongodb' in preferences:
            stack += "**Database:** MongoDB with Mongoose ODM\n"
        elif 'postgres' in preferences or 'postgresql' in preferences:
            stack += "**Database:** PostgreSQL 15+\n"
        else:
            stack += "**Database:** PostgreSQL 15+ (recommended for ACID compliance and JSON support)\n"
        
        # Additional tools
        stack += """
**Additional Tools:**
- **API Documentation:** OpenAPI/Swagger
- **Testing:** Jest/Pytest + React Testing Library
- **State Management:** Redux Toolkit or Zustand
- **Styling:** Tailwind CSS + shadcn/ui components
- **Build Tool:** Vite (fast development server)
- **Deployment:** Docker + Docker Compose
- **CI/CD:** GitHub Actions or GitLab CI
- **Monitoring:** Sentry for error tracking
"""
        
        return stack
    
    def _generate_folder_structure(self, answers: Dict, tech_stack: str) -> str:
        """Generate recommended folder structure based on tech stack."""
        if 'react' in tech_stack.lower() and 'fastapi' in tech_stack.lower():
            return """```
project-root/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/          # Reusable components
│   │   │   └── features/        # Feature-specific components
│   │   ├── pages/               # Page components
│   │   ├── services/
│   │   │   └── api.ts           # API client (DRY principle)
│   │   ├── hooks/               # Custom React hooks
│   │   ├── store/               # State management
│   │   ├── utils/               # Utility functions (DRY)
│   │   ├── types/               # TypeScript type definitions
│   │   └── App.tsx
│   ├── public/
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── models/              # Database models (SRP)
│   │   ├── routes/              # API routes (SRP)
│   │   ├── services/            # Business logic (SRP)
│   │   ├── utils/               # Utility functions (DRY)
│   │   └── main.py
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   └── requirements.txt
├── docker-compose.yml
├── .env.example
└── README.md
```"""
        else:
            return """```
project-root/
├── src/
│   ├── components/
│   ├── services/
│   ├── models/
│   ├── utils/
│   └── app.py
├── tests/
├── docker-compose.yml
└── README.md
```"""
    
    def _format_functionality(self, answers: Dict) -> str:
        """Format functionality section."""
        func = answers.get('functionality', {})
        if not func:
            return "- No specific functionality details provided"
        return '\n'.join(f"- {self._humanize_key(k)}: {v}" for k, v in func.items())
    
    def _format_users(self, answers: Dict) -> str:
        """Format user information."""
        users = answers.get('users', {})
        if not users:
            return "- General users"
        return '\n'.join(f"- {self._humanize_key(k)}: {v}" for k, v in users.items())
    
    def _format_design(self, answers: Dict) -> str:
        """Format design requirements."""
        design = answers.get('design', {})
        if not design:
            return "- Modern, clean design\n- Responsive layout\n- Intuitive user interface"
        return '\n'.join(f"- {self._humanize_key(k)}: {v}" for k, v in design.items())
    
    def _format_technical(self, answers: Dict) -> str:
        """Format technical requirements."""
        technical = answers.get('technical', {})
        if not technical:
            return "- Standard web technologies\n- Cross-browser compatibility\n- Responsive design"
        return '\n'.join(f"- {self._humanize_key(k)}: {v}" for k, v in technical.items())
    
    def _generate_functional_requirements(self, answers: Dict) -> str:
        """Generate structured functional requirements."""
        func = answers.get('functionality', {})
        
        if not func:
            return "### Core Features\n\n1. **Primary Functionality**\n   - To be determined based on product requirements\n\n"
        
        requirements = "### Core Features\n\n"
        for i, (key, value) in enumerate(func.items(), 1):
            requirements += f"{i}. **{self._humanize_key(key)}**\n"
            requirements += f"   - {value}\n\n"
        
        return requirements
    
    def _compile_additional_context(self, answers: Dict) -> str:
        """Compile any additional context not categorized."""
        context = []
        
        for category, data in answers.items():
            if isinstance(data, dict) and len(data) > 2:  # More than just basic info
                for key, value in data.items():
                    if key not in ['overview', 'summary', 'primary_use_case'] and len(value) > 10:
                        context.append(f"- **{category.title()}/{self._humanize_key(key)}:** {value}")
        
        return '\n'.join(context) if context else "None"
    
    def _extract_key_from_question(self, question: str) -> str:
        """Extract a key from question for organization."""
        # Simple key extraction - first 3-4 meaningful words
        words = question.lower().split()
        key_words = [w for w in words if len(w) > 3 and w not in 
                    ['what', 'does', 'your', 'will', 'have', 'would', 'should', 'could', 'with', 'from', 'into', 'about']]
        return '_'.join(key_words[:3]) if key_words else 'general'
    
    def _humanize_key(self, key: str) -> str:
        """Convert underscore_key to Human Readable."""
        return ' '.join(word.capitalize() for word in key.split('_'))
    
    def _get_answer_value(self, answers: Dict, category: str, key: str, default: str) -> str:
        """Safely get answer value with default."""
        return answers.get(category, {}).get(key, default)
    
    def _validate_prompt(self, prompt: str) -> bool:
        """
        Validate prompt completeness.
        
        Args:
            prompt: Generated prompt string
            
        Returns:
            True if valid, False otherwise
        """
        required_sections = [
            'Your Role',
            'Product Context',
            'SOLID Principles',
            'DRY',
            'Architecture',
            'Functional Requirements',
            'Output Format'
        ]
        
        for section in required_sections:
            if section not in prompt:
                logger.warning(f"Missing required section: {section}")
                return False
        
        # Check minimum length
        if len(prompt) < 1000:
            logger.warning(f"Prompt too short: {len(prompt)} characters")
            return False
        
        return True
    
    def _optimize_token_count(self, prompt: str) -> str:
        """
        Optimize token count while preserving information.
        
        Args:
            prompt: Original prompt
            
        Returns:
            Optimized prompt
        """
        # Remove excessive whitespace
        lines = prompt.split('\n')
        optimized_lines = []
        prev_empty = False
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if not prev_empty:  # Keep only one empty line
                    optimized_lines.append('')
                    prev_empty = True
            else:
                optimized_lines.append(line.rstrip())
                prev_empty = False
        
        optimized = '\n'.join(optimized_lines)
        
        # Rough token estimate (1 token ≈ 4 characters)
        estimated_tokens = len(optimized) / 4
        
        if estimated_tokens > 8000:
            logger.warning(f"Prompt may exceed token limit: ~{int(estimated_tokens)} tokens")
        
        return optimized.strip()


# Dependency injection helper
def get_prompt_generator(storage):
    """
    Factory function for creating PromptGenerator instances.
    
    Args:
        storage: ConversationStorage instance
        
    Returns:
        Configured PromptGenerator instance
    """
    return PromptGenerator(storage)
PYTHON_CODE

echo "✓ Created backend/services/prompt_generator.py"

echo ""
echo "=== TASK-3.1 Backend Implementation Complete ===" 
echo ""
echo "✓ Created PromptGenerator service (588 lines)"
echo "✓ Implements comprehensive prompt generation"
echo "✓ Follows SOLID principles (SRP, OCP, DIP)"
echo "✓ Applies DRY through helper methods"
echo "✓ Includes architecture suggestions"
echo "✓ Tech stack recommendations"
echo "✓ Folder structure generation"
echo "✓ Token optimization"
echo "✓ Prompt validation"
echo ""
echo "Next: Run test script to create unit tests for this service"
