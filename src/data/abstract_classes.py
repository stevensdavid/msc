from abc import ABC, abstractmethod
from typing import List, Optional

import numpy as np
import torch
from torch.utils.data import Dataset
from util.dataclasses import DataShape, GeneratedExamples, LabelDomain
from util.enums import DataSplit


class AbstractDataset(Dataset, ABC):
    def __init__(self) -> None:
        super().__init__()
        self.mode: DataSplit = None

    @abstractmethod
    def random_targets(self, shape: torch.Size) -> torch.Tensor:
        ...

    def set_mode(self, mode: DataSplit) -> None:
        self.mode = mode

    def __len__(self) -> int:
        if self.mode is None:
            raise ValueError("Please call 'set_mode' before using data set")
        return self._len()

    def __getitem__(self, index: int):
        if self.mode is None:
            raise ValueError("Please call 'set_mode' before using data set")
        return self._getitem(index)

    def stitch_examples(
        self, real_images, real_labels, fake_images, fake_labels
    ) -> List[GeneratedExamples]:
        def stitch_image(real, fake):
            if real.shape[0] == 1:
                real = torch.repeat_interleave(real, 3, dim=0)
                fake = torch.repeat_interleave(fake, 3, dim=0)
            merged = np.concatenate((real, fake), axis=2)
            return np.moveaxis(merged, 0, -1)  # move channels to end

        return [
            GeneratedExamples(stitch_image(real, fake), f"{label} to {target}")
            for real, fake, label, target in zip(
                real_images, fake_images, real_labels, fake_labels
            )
        ]

    def normalize(self, x: np.ndarray) -> np.ndarray:
        """Scale from [0,1] to [-1,1]

        Args:
            x (np.ndarray): Image with values in range [0,1]

        Returns:
            np.ndarray: Image with values in range [-1,1]
        """
        return 2 * x - 1

    def denormalize(self, x: np.ndarray) -> np.ndarray:
        """Scale from [-1,1] to [0,1]

        Args:
            x (np.ndarray): Image with values in range [-1,1]

        Returns:
            np.ndarray: Image with values in range [0,1]
        """
        return (x + 1) / 2

    @abstractmethod
    def _len(self) -> int:
        ...

    @abstractmethod
    def _getitem(self, index):
        ...

    @abstractmethod
    def data_shape(self) -> DataShape:
        ...

    @abstractmethod
    def performance(self, real_images, real_labels, fake_images, fake_labels) -> dict:
        ...

    @abstractmethod
    def label_domain(self) -> Optional[LabelDomain]:
        ...

    def has_performance_metrics(self) -> bool:
        return True
