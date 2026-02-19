# Data Output Schema

This document defines the standardized output produced by the Instagram Data Parser Library.

All supported Instagram JSON files are converted into rows with the same column structure.

## Unified Output Schema

Each supported Instagram JSON file is converted into rows with the same columns:

| column       | meaning |
|-------------|---------|
| object_type  | what content the action relates to (post, reel, story) |
| action_type  | what the user did (like, comment, poll_response) |
| target       | what was acted on (usually a link; may be blank if not available) |
| actor        | the owner/creator of the content |
| value        | extra context (e.g., comment text, poll choice, like marker) |
| timestamp    | when the action happened (unix timestamp) |

### Target + Value by content type

| object_type | action_type                | target (what)     | actor (who)           | value (what to store)                     | timestamp |
|------------|----------------------------|-------------------|-----------------------|-------------------------------------------|----------|
| post       | like, comment              | post link         | owner of post         | like marker OR comment text               | yes      |
| reel       | comment                    | (no link)         | owner of reel         | comment text                              | yes      |
| story      | like, poll_response        | (no link)         | owner of story        | like marker OR poll response value        | yes      |
