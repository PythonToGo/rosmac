"""rosmac 공통 예외 — exit code 규약의 단일 소스 (P5.2).

규약: 0 성공 / 1 실행 실패 / 2 사용법·설정 오류.
표출은 cli.main()이 한 곳에서 담당한다 (rich 패널 + 처방).

RosmacError가 RuntimeError를 상속하는 이유: 관찰 도구들(psview 등)의
`except RuntimeError` 방어선이 rosmac 내부 실패를 계속 잡아야 하기 때문.
"""


class RosmacError(RuntimeError):
    """실행 실패 (exit 1). message는 원인, hint는 사용자가 칠 처방."""

    def __init__(self, message: str, hint: str | None = None, exit_code: int = 1) -> None:
        super().__init__(message)
        self.hint = hint
        self.exit_code = exit_code


class UsageError(RosmacError):
    """사용법·설정 오류 (exit 2) — 인자/설정을 고치면 되는 종류."""

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message, hint, exit_code=2)
