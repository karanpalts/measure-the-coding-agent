"""Checks on the path a run took, read from its trace. The score says where a run ended; these
say how it got there. Each check is a function of one trace that returns True when the run did
the thing it looks for.

  uv run checks.py results/v1

Add your own: write a function below and add it to CHECKS.
"""
import glob, json, os, re, sys

EDITS = ("edit_file", "write_file")


def calls(trace):
    return [c for t in trace["turns"] for c in t["calls"]]


def ran_tests(call):
    return call["name"] == "run" and "pytest" in call["args"].get("command", "")


def edited_without_testing_after(trace):
    """It changed a file and never ran the tests after its last change."""
    cs = calls(trace)
    edits = [i for i, c in enumerate(cs) if c["name"] in EDITS]
    if not edits:
        return False
    return not any(ran_tests(c) for c in cs[edits[-1] + 1:])


HISTORY = re.compile(r"\bgit\s+(log|show|cherry-pick|reflog)")


def read_git_history(trace):
    """It looked at the repository's history: log, show, cherry-pick."""
    commands = [c["args"].get("command", "") for c in calls(trace) if c["name"] == "run"]
    return any(HISTORY.search(command) for command in commands)


def same_call_three_times(trace):
    """It made the same call, with the same arguments, three or more times. Running the tests
    twice is normal. Three identical calls is usually a run going round in a circle."""
    seen = {}
    for c in calls(trace):
        key = (c["name"], json.dumps(c["args"], sort_keys=True))
        seen[key] = seen.get(key, 0) + 1
    return max(seen.values(), default=0) >= 3


def edited_without_reading(trace):
    """It tried to edit a file before reading it (the tool refuses; the attempt is the signal)."""
    return any(c["name"] in EDITS and isinstance(c["result"], dict) and "before" in str(c["result"].get("error", ""))
               for c in calls(trace))



def edited_outside_src(trace):
    """It edited or wrote a file outside src/."""
    return any(
        c["name"] in EDITS and not os.path.normpath(c["args"].get("path", "")).startswith("src" + os.sep)
        for c in calls(trace)
    )


CHECKS = [edited_without_testing_after, read_git_history, same_call_three_times, edited_without_reading, edited_outside_src]


def main(folder):
    traces = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(folder, "*.json")))]
    print(f"{folder}: {len(traces)} runs\n")
    print(f"  {'check':<32}{'runs':>8}{'of which passed':>18}")
    for check in CHECKS:
        hit = [t for t in traces if check(t)]
        passed = sum(t["record"]["success"] for t in hit)
        print(f"  {check.__name__:<32}{len(hit):>4} / {len(traces):<4}{passed:>10} / {len(hit)}")
    print("\nA run can pass and still have taken a path you would not accept. The last column is those runs.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/v1")
