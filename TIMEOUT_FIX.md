# ✅ Timeout Increased

## Issue
The user requested to increase the timeout time, likely due to intermittent failures causing the system to fall back to "mocked" templates.

## Fix Implemented
1. **Updated `backend/services/model_checker.py`**:
   - **Model Fetching Timeout:** Increased from 10s to **30s**.
   - **LLM Request Timeout:** Set default request timeout to **60s** (was default, likely shorter).

## Result
- **Reduced Fallbacks:** The system will wait longer for the LLM to respond before giving up and using templates.
- **Better Stability:** More resilient to network latency or slow API responses.

## Verification
1. **Restart your investigation.**
2. The system should be more robust against delays.
