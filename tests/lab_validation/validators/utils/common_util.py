from typing import Any, Optional

from pandas import DataFrame
from pybatfish.client.session import Session
from pybatfish.datamodel.answer import TableAnswer
from pybatfish.question.question import QuestionBase


class MockSession(Session):
    """Mock session providing object storage and retrieval."""

    def __init__(self, load_questions: bool = False, **params: Any) -> None:
        super(MockSession, self).__init__(
            host="localhost", load_questions=load_questions, **params
        )

    def _is_api_healthy(self) -> bool:
        return True


class MockTableAnswer(TableAnswer):
    def __init__(self, frame_to_use: DataFrame = DataFrame()) -> None:
        self._frame = frame_to_use

    def frame(self) -> DataFrame:
        return self._frame


class MockQuestion(QuestionBase):
    def __init__(self, answer: Optional[TableAnswer] = None) -> None:
        self._answer = answer if answer is not None else MockTableAnswer()

    def answer(self, *args: Any, **kwargs: Any) -> TableAnswer:
        return self._answer
