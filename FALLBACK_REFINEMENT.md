# ✅ Fallback Logic Refined

## Issue
The user reported a nonsensical exchange where the AI replied "That sounds interesting!" to the user saying "hi".

## Root Cause
The user's input "hi" was too short, triggering the "follow-up" logic. The LLM generation likely failed (or was skipped), causing the system to use a **fallback template**. The previous fallback templates for the `START` state assumed the user had given a partial answer, not a greeting.

## Fix Implemented
1. **Updated `backend/services/question_generator.py`**:
   - Changed the `START` state fallback templates to be neutral and directive.
     - *Old:* "That sounds interesting! Could you give me a bit more detail..."
     - *New:* "Could you tell me a bit about the product idea you have in mind?"

## Result
- **Natural Handling of Greetings:** If the user says "hi" and the system falls back to templates, it will politely redirect to the product question without sounding confused or sarcastic.

## Verification
1. **Restart your investigation.**
2. Say "hi" or "hello".
3. The response should be a polite prompt to describe your idea.
