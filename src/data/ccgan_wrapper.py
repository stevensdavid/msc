from collections import defaultdict
from typing import Tuple

import numpy as np
from torch import Tensor, tensor
from torch.utils.data import Dataset
from util.enums import DataSplit, VicinityType

from data.abstract_classes import AbstractDataset


class CcGANDatasetWrapper(AbstractDataset):
    def __init__(
        self,
        dataset: Dataset,
        type: VicinityType,
        sigma: float,
        hyperparam: float,
        clip=True,
    ) -> None:
        self.type = type
        self.dataset = dataset
        self.sigma = sigma
        self.labels = defaultdict(list)
        self.hyperparam = hyperparam
        self.clip = clip
        for idx in range(len(self.dataset)):
            _, y = dataset[idx]
            self.labels[y].append(float(idx))
        self.unique_labels = np.asarray(self.labels.keys())
        self.min_label = np.min(self.unique_labels)
        self.max_label = np.max(self.unique_labels)

    def _getitem(self, _: int) -> Tuple[Tensor, Tensor]:
        sample_label = np.random.choice(self.unique_labels)
        noisy_label = sample_label + np.random.normal(scale=self.sigma)
        if self.clip:
            noisy_label = np.clip(noisy_label, self.min_label, self.max_label)

        if self.type is VicinityType.HARD:
            candidate_labels = self.unique_labels[
                np.abs(self.unique_labels - noisy_label) <= self.hyperparam
            ]
            candidate_idxs = [
                idx for label in candidate_labels for idx in self.labels[label]
            ]
            image_idx = np.random.choice(candidate_idxs)
            image, _ = self.dataset[image_idx]
            weight = 1
            target_label = np.random.uniform(
                noisy_label - self.hyperparam, noisy_label + self.hyperparam
            )
            if self.clip:
                target_label = np.clip(target_label, self.min_label, self.max_label)
            target_weight = 1
        elif self.type is VicinityType.SOFT:
            # TODO
            raise NotImplementedError("TODO")
        return (
            image,
            {
                "labels": tensor(noisy_label),
                "loss_weights": tensor(weight),
                "target_labels": tensor(target_label),
                "target_weights": tensor(target_weight),
            },
        )

    def _len(self) -> int:
        return len(self.dataset)

    def set_mode(self, mode: DataSplit) -> None:
        self.dataset.set_mode(mode)
