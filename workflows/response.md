1. Detect target MQL version and file type
   - Tool: detect_mql_version
   - Args: request
   - Look for: mql_version, script_type, confidence, rationale.

2. Load relevant MetaTrader context
   - Tool: read_context
   - Args: resources such as style.md plus relevant domain files like trade.md, risk-management.md, indicator.md, expert-advisor.md, script.md, chart.md, terminal.md, strategies.md, object.md, and platform.md
   - Look for: syntax, event flow, and version-specific guidance.

3. Plan the implementation
   - Tool: plan_mql_script
   - Args: request, mql_version, script_type, context_notes
   - Look for: handlers, inputs, logic, APIs, and output target.

4. Write and compile the MQL source file
   - Tool: write_mql_file
   - Args: request, mql_version, script_type, plan, output_path if needed
   - Look for: file_path, compilation_log, errors, warnings.

5. Build final structured output
   - Tool: build_output
   - Args: script_type, mql_version, file_path, compilation_log, errors, warnings
   - Look for: a valid OutputModel ready to return.

Rules:
- Unless stated in the prompt, always detect whether the request is for MQL4 or MQL5 before planning or writing code.
- Use read_context to ground the implementation in the provided MetaTrader guidance.
- The final stage must compile the generated .mq4 or .mq5 file using MetaEditor.
- Prefer version-specific APIs and event handlers appropriate to the detected MQL version.
- If compilation fails, fix the code and recompile until successful, ensuring the output is valid and complete.
- Always call build_output last.
