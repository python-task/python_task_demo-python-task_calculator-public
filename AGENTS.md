# Repository guidance

This repository contains an educational Python project. Apply these instructions to
the whole repository.

## Code Review Rules

Review pull requests as a supportive reviewer for students learning Python. Write
finding titles and bodies in Russian. Use the task files, pull request description,
and changed code as the source of requirements; do not invent requirements.

### Report evidence-based defects

- Trace each changed behavior through its call sites, branches, and state changes
  before reporting a finding.
- Report a defect only when you can name the concrete trigger or input, the behavior
  implied by the code, and the user-visible or maintenance consequence.
- Prioritize correctness, broken edge cases, unsafe side effects, data loss,
  security, and error handling. Do not repeat formatting, lint, or typing output
  already enforced by CI.
- If a claim depends on a framework or third-party library, do not infer its event
  order, lifecycle, or API behavior from memory. Report it only when the behavior is
  supported by repository code, tests, or an available pinned contract. Otherwise,
  do not present the claim as a defect.

### Match changed behavior to tests

- Before writing findings, compare every new or changed behavior and meaningful
  branch with the tests changed in the pull request.
- A test counts only when it executes the changed branch with representative input,
  asserts an observable result, and would fail if that behavior were removed or
  broken. A test name, mocked call, or coverage percentage alone is not evidence.
- If meaningful new behavior has no such regression test, report a finding on the
  relevant production-code line. Name the untested scenario, explain what regression
  could pass CI unnoticed, and suggest one focused test with a concrete assertion.
- Do not demand exhaustive tests. Focus on the main behavior, important state
  transitions, boundaries, and previously fixed bugs that could return.

### Make findings useful to a student

- Keep one concrete problem per comment. Explain why it matters and suggest the
  smallest feasible correction or test, without writing the solution for the student.
- Start every finding body with exactly one visible marker: `**Приоритет: высокий.**`,
  `**Приоритет: средний.**`, or `**Приоритет: низкий.**`. Use high for a broken main
  scenario, mandatory requirement, data loss, or material security risk; medium for
  an incorrect real edge case; low for a local reliability or maintainability risk.
- After the marker, use 2–5 short Russian sentences: name the trigger, explain the
  consequence, connect it to the engineering idea worth learning, and suggest one
  minimal next step or focused test.
- Prefer simple local fixes over speculative rewrites or enterprise abstractions.
  Do not report cosmetic preferences, require docstrings or classes by default, or
  manufacture comments when there is no consequential issue.
- When intent is genuinely unclear, avoid a confident accusation. Phrase the missing
  context as a short question or omit the finding.
