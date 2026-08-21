# Search Query Bug Analysis

## The Problem
When pasting a large search query (like a full job description) into the search bar, the progress bar stays at 0% and then disappears, with no candidates found.

## Root Cause
The search query fails because it contains unescaped special characters (e.g., `-`, `/`, `+`) which are interpreted as syntax operators by the SQLite FTS5 (Full-Text Search) engine. 

For example, in the query:
- `"hands-on"`: FTS5 misinterprets the `-` and throws `sqlite3.OperationalError: no such column: on` because it thinks it is a column filter.
- `"Java/J2EE"`: FTS5 throws `sqlite3.OperationalError: fts5: syntax error near "/"` because `/` is an illegal character for barewords.

### Where it happens in the code
In `src/candidate_intelligence_platform/search/ast_parser.py`, the backend attempts to clean up illegal FTS5 characters:
```python
# Remove FTS5 illegal characters
fts_query = re.sub(r'[!()*^{}\[\]~:]', ' ', fts_query)
```
This regular expression misses characters like `-`, `/`, and `+`.

When the unescaped query is executed by `execute_fts_query` in `hybrid_searcher.py`, the database throws a syntax error exception. 

### Why the UI fails silently
The `/search/stream` API endpoint in `api/routes/search.py` catches this database exception and yields an `"ERROR"` event back to the frontend:
```python
except Exception as e:
    yield f"data: {{json.dumps({{'stage': 'ERROR', 'progress': 100, 'message': str(e), 'status': 'FAILED'}})}}\n\n"
```
The frontend UI does not handle this error state correctly. Instead of displaying a helpful error message to the user, the UI progress bar simply resets and disappears, leaving the user with an empty result set and no context about the failure.

## Recommended Fix
1. **Backend**: Update the regex in `ast_parser.py` to strip out `-`, `/`, `+`, and any other problematic punctuation, or properly enclose the search string in double quotes so that FTS5 treats them as string literals rather than operators.
2. **Frontend**: Update the UI search component to listen for the `ERROR` stage and display a toast notification or error message so failures aren't silent.
