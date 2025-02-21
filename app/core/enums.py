from enum import Enum

class FashnCategory(Enum):
    TOPS = "tops"
    BOTTOMS = "bottoms"
    OVERWEARS = "overwears"
    FULLBODYS = "fullbodys"

    @staticmethod
    def list():
        """Returns a list of all valid category values."""
        return [category.value for category in FashnCategory]

