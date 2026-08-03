from dataclasses import dataclass

from app.core.exceptions import ApplicationError


@dataclass(eq=False, kw_only=True)
class AttributeNotExistError(ApplicationError):
    field: str
    code: str = "ATTRIBUTE_NOT_EXIST"
    status: int = 400

    @property
    def message(self) -> str:
        return "This attribute does not exist"

    @property
    def detail(self) -> dict:
        return {"attribute": self.field}
