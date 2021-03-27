from enum import Enum, auto


class DataSplit(Enum):
    TRAIN = auto()
    VAL = auto()
    TEST = auto()


class FrequencyMetric(Enum):
    EPOCHS = auto()
    ITERATIONS = auto()