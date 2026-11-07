# Aesthetic ranking artifact development

Change the HTML review product that lets a user inspect and rank design
decisions. This product begins with recorded decisions and previews. It does not
own creative generation.

## Owners and callers

Load only the files needed by the defect or contract change.

| File | Responsibility |
| --- | --- |
| `scripts/harness_article.py` | Composes the established ranking article. |
| `scripts/harness_round.py` | Checks cohort scope and the question a rank answers. |
| `scripts/harness_specimens.py` | Renders individually rankable decisions. |
| `scripts/harness_controls.py` | Adds ranking controls without rewriting evidence. |
| `scripts/deliver.py` | Publishes one round and returns the URL, key, question, and review images. |
| `screen/` | Owns article and control behavior in the browser. |

`bootstrap_harness.py` is a parser and re-export facade. Put behavior in its
owning seam. `deliver.py` calls the article, publish, review-image, and idle-state
steps as one delivery boundary.

Do not load generation prompts, model adapters, or art-direction doctrine unless
the failing acceptance path crosses that boundary. A rank records the user's
judgment. It never becomes an agent score.

## Proof

Start with the focused failing test. Select the narrowest owner suite.

```bash
python3 -B -m unittest discover -s first/aesthetic/scripts -p 'test_article*.py'
python3 -B -m unittest discover -s first/aesthetic/scripts -p 'test_deliver.py'
python3 -B -m unittest discover -s first/aesthetic/scripts -p 'test_companion_settings.py'
```

When browser behavior changes, inspect rendered desktop and narrow views. Then
run the package gate from the repository root.
