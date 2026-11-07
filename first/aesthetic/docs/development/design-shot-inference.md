# Design Shot inference development

Change how an agent turns user constraints and visual evidence into a checked
Shot. This product ends at a generated or refined graphic proposal. It does not
own the review page.

## Owners and callers

Load only the files needed by the defect or contract change.

| File | Responsibility |
| --- | --- |
| `scripts/direction_context.py` | Selects and budgets Design-Inference Context. |
| `scripts/text_to_graphics.py` | Validates scene data and routes generation or refinement. |
| `scripts/graphics_generation.py` | Compiles the generation pass and calls the graphics adapter. |
| `scripts/graphics_flow.py` | Returns the next action and carries bounded Shot corrections. |
| `scripts/editorial_workflow.py` | Supplies brief, preference, and corpus evidence when their schema is in scope. |

`text_to_graphics.py` calls the generation adapter. The generation adapter calls
the context compiler. The compiler reads only enumerated Design-Inference
evidence and doctrine. Keep priority, loading tier, workflow role, and
publication channel as separate fields.

Do not load article layout, companion chrome, or publication code unless the
failing acceptance path crosses that boundary. A screenshot is evidence for
the proposal, not permission to change the review product.

## Proof

Start with the focused failing test. Run the owning tests after the change.

```bash
python3 -B -m unittest discover -s first/aesthetic/scripts -p 'test_direction_context.py'
python3 -B -m unittest discover -s first/aesthetic/scripts -p 'test_text_to_graphics.py'
python3 -B -m unittest discover -s first/aesthetic/scripts -p 'test_graphics_flow.py'
```

Use `test_editorial_workflow.py` only when the evidence schema changed. Then run
the package gate from the repository root.
