---
applyTo: '*.py'
---

# Code Comment Style Guidelines
To ensure clarity and maintainability in our codebase, we adopt an **Intent-First Commenting Style**. This style focuses on the intent behind the code rather than its mechanics, making it easier for developers to understand the purpose of each section at a glance.


## Intent-First Commenting Style

1. **Intent over mechanics**

   * **What:** Briefly state *why* the code exists or *what problem* it solves.
   * **How:** Only when non-obvious, add *how* (e.g. “using binary search in O(log n) time”).
   * **Avoid:** Don’t describe *what* the code literally does.

2. **Active-voice, present tense**

   * “Sorts the list by timestamp.”
   * “Handle missing keys with default values.”

3. **Minimal context, maximal clarity**

   * One sentence per comment.
   * Capitalize first word, end with a period.
   * Keep ≤ 72 characters.

4. **Consistent prefixes for special notes**

   * **`NOTE:`** for side-effects or caveats
   * **`TODO(owner,YYYY-MM-DD):`** for actionable tasks
   * **`HACK:`** for unsafe or temporary workarounds

5. **Section headers for grouping**

   * Use a single-line divider and title:

     ```python
     # ——— Data validation ———
     ```
   * Place above related functions or logic blocks.

6. **Reference guidance, not implementation**

   * Cite standards, algorithms, or ticket numbers when relevant:

     ```python
     # NOTE: uses LRU eviction per RFC 2616 Section 13.7.
     ```

7. **Inline comments sparingly**

   * Only for edge-cases or surprising behavior:

     ```python
     value = lookup(x)  # NOTE: returns None on cache miss
     ```

---

#### Example

```python
# ——— Authentication flow setup ———

def authenticate(user):
    """Validate credentials and return JWT token."""
    # Intent: prevent brute-force by throttling attempts.
    throttle(user, max_attempts=5)

    token = generate_jwt(user)  # NOTE: expires in 15 minutes.

    # TODO(@jane,2025-06-01): log IP address on failed attempts.
    return token
```
