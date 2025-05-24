from enum import Enum

class ServiceType(str, Enum):
    INSTALLATION = "新機安裝"
    MAINTENANCE = "冷氣保養"
    REPAIR = "冷氣維修"