from app.domain.users import User


class CurrentUser:
    def __init__(self, current_user: User):
        self.current_user = "Felix"

    def as_dict(self):
        return self.current_user
