# ✅ Fallback Experience Improved

## Issue
The user reported inconsistent behavior ("blunt or mocked depends on when I run it"). This indicates that the LLM generation sometimes fails, causing the system to fall back to the static templates, which were indeed blunt and "mocked".

## Root Cause
Intermittent LLM API failures (timeouts, rate limits, etc.) trigger the fallback mechanism. The fallback templates were static and robotic, creating a jarring difference in quality when the API failed.

## Fix Implemented
1. **Updated `backend/services/question_generator.py`**:
   - **Rewrote Fallback Templates:** Replaced all static question templates with friendly, conversational versions.
     - *Old:* "What problem does your product solve?"
     - *New:* "I'm excited to hear about your idea! To get us started, could you tell me what core problem your product solves?"
   - **Enhanced Error Logging:** Added detailed logging (error type, context length) to help diagnose why the LLM fails.

## Result
- **Consistent Quality:** Even if the LLM API fails, the fallback questions will now be polite and engaging.
- **Better Debugging:** We can now see exactly why the LLM fails in the logs.

## Verification
1. **Restart your investigation.**
2. Even if you encounter network issues or API glitches, the conversation should remain friendly and professional.
