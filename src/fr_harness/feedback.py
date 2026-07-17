import re

from fr_harness.models import Feedback


def parse_pytest_result(returncode: int, stdout: str, stderr: str) -> Feedback:
    output = "\n".join(part.strip() for part in (stdout, stderr) if part.strip())
    failed_tests = list(dict.fromkeys(re.findall(r"(?m)^FAILED\s+(\S+)", output)))
    summary = (output or f"pytest exited with code {returncode}")[:2_000]
    return Feedback(
        passed=returncode == 0,
        summary=summary,
        failed_tests=failed_tests,
    )
