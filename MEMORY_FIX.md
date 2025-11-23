# ✅ Memory Retrieval Fix

## Issue
The user reported that questions seemed "circular and redundant", indicating that the AI was forgetting previous context.

## Root Cause
In `_generate_category_question` (which handles transitions between topics like Functionality -> Users), the **RAG context (retrieved memory)** was being passed to the function but **ignored** in the prompt construction. The AI only saw the last 6 messages. If a relevant detail was mentioned earlier, the AI wouldn't know about it.

## Fix Implemented
1. **Updated `backend/services/question_generator.py`**:
   - Modified `_generate_category_question` to explicitly include the `context` (RAG chunks) in the `user_prompt`.
   - Added a section `Relevant Context from previous topics:` to the prompt.

## Result
- **Better Continuity:** The AI now "remembers" relevant details from the entire conversation, not just the last few messages.
- **Reduced Redundancy:** It should stop asking for information you've already provided.

## Verification
1. **Restart your investigation.**
2. Mention a detail early on (e.g., "My users are elderly").
3. Later, when the topic switches to "Users" or "Design", the AI should acknowledge this detail instead of asking "Who are your users?" from scratch.
