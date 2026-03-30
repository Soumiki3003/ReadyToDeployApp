from pydantic import BaseModel, PositiveInt


class Paginated(BaseModel):
    page: PositiveInt = 1
    page_size: PositiveInt = 10
