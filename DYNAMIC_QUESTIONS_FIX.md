# ✅ Dynamic Question Generation Enabled

## Issue
The user reported that the conversation felt like "mock messages" and wasn't context-aware.

## Root Cause
The `QuestionGenerator` service was using **static templates** for the main category questions (e.g., "Who are the primary users?"). It only used the LLM for follow-up questions. This made the conversation feel robotic and disconnected from previous answers.

## Fix Implemented
1. **Updated `backend/services/question_generator.py`**:
   - Modified `_generate_category_question` to use the LLM to generate questions dynamically.
   - Created a new system prompt that instructs the LLM to:
     - Focus on the current category (e.g., Users, Design).
     - Reference previous answers to maintain context.
     - Be conversational and professional.
   - Added fallback to templates only if the LLM generation fails.
   - Updated `generate_next_question` to accept conversation history (`messages`).

2. **Updated `backend/services/conversation_service.py`**:
   - Updated `process_answer` and `skip_current_question` to pass the full conversation history to the generator.

## Result
The chatbot will now generate unique, context-aware questions for each category, making the investigation feel like a real conversation with an expert product manager.

## Verification
1. Start a new investigation.
2. Answer the first question.
3. The next question should be specific to your answer and the new category, not a generic template.
