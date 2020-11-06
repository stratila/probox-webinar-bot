from enum import IntEnum


class BotSate(IntEnum):
    START = 1
    PHONE = 2
    REGISTRATION_START = 3
    COURSE_CHOICE = 4
    SMART_HOUSE_CHOICE = 5
    PYTHON_CHOICE = 6
    JAVASCRIPT_CHOICE = 7


class Course(IntEnum):
    SMART_HOUSE = 1
    PYTHON = 2
    JAVASCRIPT = 3
