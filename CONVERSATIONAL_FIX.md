# ✅ Conversational Quality Improvements

## Issue
The user reported that the questions were "blunt" and didn't seem to consider previous context, despite the move to dynamic generation.

## Root Cause
1. **Prompt Constraints:** The system prompt explicitly instructed the LLM to "Return ONLY the question text" and "Keep under 20 words", which stripped away natural conversational elements (e.g., "That's interesting...").
2. **Context Parsing:** There was a potential issue in how the conversation history was being built. The code was comparing `msg.role` (an Enum) to a string `'assistant'`, which might have failed in some cases, leading to an empty or malformed context history being sent to the LLM.

## Fix Implemented
1. **Updated `backend/services/question_generator.py`**:
   - **Improved Prompts:** Updated system prompts for both category and follow-up questions to explicitly ask for "conversational and professional" tone and to "use a brief bridge if appropriate".
   - **Relaxed Constraints:** Increased the word limit for follow-up questions to 30 words to allow for more natural phrasing.
   - **Fixed Context Building:** Updated the logic to correctly handle `MessageRole` enums when constructing the conversation history string (`msg.role.value`).

## Result
The chatbot should now:
- Acknowledge your previous answers (e.g., "That's a great insight about X...").
- Ask more natural, less robotic questions.
- Maintain better context throughout the conversation.

## Verification
1. **Restart your investigation.**
2. Provide a detailed answer to the first question.
3. The next question should acknowledge your detail and flow naturally, rather than abruptly changing topics or asking a blunt question.
