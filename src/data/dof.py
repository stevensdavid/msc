import json
import os
from typing import List, Tuple

import numpy as np
import torch
from PIL import Image
from torchvision import transforms
from util.dataclasses import DataShape, LabelDomain
from util.enums import DataSplit

from data.abstract_classes import AbstractDataset


class DepthOfField(AbstractDataset):
    def __init__(self, mirflickr_root: str, unsplash_root: str, image_size=500) -> None:
        super().__init__()
        self.images, self.labels = self.preprocess(mirflickr_root, unsplash_root)
        num_images = len(self.labels)
        # Four splits to support training auxiliary classifiers, etc. 55-15-15-15
        self.len_train = int(np.floor(0.55 * num_images))
        self.len_val = int(np.floor(0.15 * num_images))
        self.len_test = int(np.floor(0.15 * num_images))
        self.len_holdout = int(np.ceil(0.15 * num_images))
        transformations = [
            transforms.Resize(image_size),
            transforms.ToTensor(),
        ]
        self.train_transform = transforms.Compose(
            [transforms.RandomHorizontalFlip()] + transformations
        )
        self.val_transform = transforms.Compose(transformations)

    def preprocess(
        self, mirflickr_root, unsplash_root
    ) -> Tuple[List[str], List[float]]:
        label_filename = "f_stops.json"
        all_images = []
        all_labels = []
        for data_dir in [mirflickr_root, unsplash_root]:
            with open(os.path.join(data_dir, label_filename), "r") as f:
                file_label_mapping = json.load(f)
            all_images += [
                os.path.join(data_dir, "images", f"{name}.jpg")
                for name in file_label_mapping.keys()
            ]
            all_labels += file_label_mapping.values()
        return all_images, all_labels

    def random_targets(self, shape: torch.Size) -> torch.Tensor:
        return torch.rand(shape)

    def _get_idx_offset(self) -> int:
        if self.mode is DataSplit.TRAIN:
            return 0
        elif self.mode is DataSplit.VAL:
            return self.len_train
        elif self.mode is DataSplit.TEST:
            return self.len_train + self.len_val
        elif self.mode is DataSplit.HOLDOUT:
            return self.len_train + self.len_val + self.len_test

    def _len(self) -> int:
        if self.mode is DataSplit.TRAIN:
            return self.len_train
        elif self.mode is DataSplit.VAL:
            return self.len_val
        elif self.mode is DataSplit.TEST:
            return self.len_test
        elif self.mode is DataSplit.HOLDOUT:
            return self.len_holdout

    def _getitem(self, index):
        index += self._get_idx_offset()
        filename, label = self.images[index], self.labels[index]
        image = Image.open(filename)
        if self.mode is DataSplit.TRAIN:
            image = self.train_transform(image)
        else:
            image = self.val_transform(image)
        label = torch.tensor(label, dtype=torch.float32)
        image = self.normalize(image)
        return image, label

    def data_shape(self) -> DataShape:
        x, y = self[0]
        return DataShape(y_dim=y.shape[0], n_channels=x.shape[0], x_size=x.shape[1])

    def performance(self, real_images, real_labels, fake_images, fake_labels) -> None:
        return None

    def label_domain(self) -> LabelDomain:
        return LabelDomain(0, 1)

    def has_performance_metrics(self) -> bool:
        return False


if __name__ == "__main__":
    dataset = DepthOfField(
        unsplash_root="F:\\Data\\unsplash-full\\data",
        mirflickr_root="F:\\Data\\mirflickr\\processed",
    )
    dataset.set_mode(DataSplit.TRAIN)
    x, y = dataset[0]
    x = dataset.denormalize(x)
    import matplotlib.pyplot as plt

    plt.imshow(x.permute(1, 2, 0))
    plt.show()
