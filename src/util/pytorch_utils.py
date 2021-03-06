import hashlib
import os
import random
from typing import List, Tuple

import numpy as np
import torch
from PIL import Image
from torch import Tensor, nn
from torchvision.transforms.functional import normalize


class ConditionalInstanceNorm2d(nn.Module):
    def __init__(self, embedding_dim, feature_dim):
        super().__init__()
        self.feature_dim = feature_dim
        self.instance_norm = nn.InstanceNorm2d(feature_dim, affine=False)
        self.gamma = nn.Linear(embedding_dim, feature_dim, bias=False)
        self.beta = nn.Linear(embedding_dim, feature_dim, bias=False)

    def forward(self, x: Tensor, y: Tensor) -> Tensor:
        out = self.instance_norm(x)
        gamma = self.gamma(y).view(-1, self.feature_dim, 1, 1)
        beta = self.beta(y).view(-1, self.feature_dim, 1, 1)
        out = out + beta + out * gamma
        return out


def ndarray_hash(x: np.ndarray) -> int:
    hasher = hashlib.sha256()
    hasher.update(x.tobytes())
    return hasher.hexdigest()


def img_to_numpy(x: torch.Tensor) -> np.ndarray:
    return np.moveaxis(x.cpu().numpy(), 0, -1)


def invert_normalize(x: torch.Tensor, mean: List[float], std: List[float]):
    if len(x.shape) == 3:
        x = x.unsqueeze(0)
    x = x.clone().movedim(1, -1)
    mean = torch.as_tensor(mean)
    std = torch.as_tensor(std)
    x = x * std + mean
    return x.movedim(-1, 1).squeeze()


def relativistic_loss(real_sources, real_average, fake_sources, sample_weights):
    fake_average = torch.mean(fake_sources)
    real_loss = torch.mean(sample_weights * (real_sources - fake_average + 1) ** 2)
    fake_loss = torch.mean((fake_sources - real_average - 1) ** 2)
    return (real_loss + fake_loss) / 2


def stitch_images(images: List[torch.Tensor], dim=2) -> np.ndarray:
    for idx, image in enumerate(images):
        if image.shape[0] == 1:
            if isinstance(image, torch.Tensor):
                images[idx] = torch.repeat_interleave(image, 3, dim=0)
            elif isinstance(image, np.ndarray):
                images[idx] = np.repeat(image, 3, axis=0)
    merged = np.concatenate(images, axis=dim)
    return np.moveaxis(merged, 0, -1)  # move channels to end


def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def set_seeds(seed: int):
    np.random.seed(seed)
    torch.manual_seed(seed)


def seed_worker(worker_id):
    worker_seed = torch.initial_seed() % 2 ** 32
    np.random.seed(worker_seed)
    random.seed(worker_seed)


def conv2d_output_size(
    input_size: int, kernel_size: int, padding: int, stride: int
) -> int:
    output_size = 1 + (input_size - kernel_size + 2 * padding) / stride
    assert output_size.is_integer()
    return int(output_size)


def _optimizer_checkpoint_path(checkpoint_dir, step) -> str:
    return os.path.join(checkpoint_dir, f"optimizers_{step}.pt")


def save_optimizers(generator_opt, discriminator_opt, step, checkpoint_dir):
    file = _optimizer_checkpoint_path(checkpoint_dir, step)
    torch.save(
        {"g_opt": generator_opt.state_dict(), "d_opt": discriminator_opt.state_dict()},
        file,
    )


def load_optimizer_weights(
    generator_opt, discriminator_opt, step, checkpoint_dir, map_location
):
    file = _optimizer_checkpoint_path(checkpoint_dir, step)
    opt_state = torch.load(file, map_location=map_location)
    generator_opt.load_state_dict(opt_state["g_opt"])
    discriminator_opt.load_state_dict(opt_state["d_opt"])


def pad_to_square(pil_image: Image):
    """Adapted from https://note.nkmk.me/en/python-pillow-add-margin-expand-canvas/"""
    w, h = pil_image.size
    side = max(w, h)
    if w == h:
        return pil_image
    # pad with black
    result = Image.new(pil_image.mode, (side, side), (0, 0, 0))
    if w > h:
        result.paste(pil_image, (0, (w - h) // 2))
    else:
        result.paste(pil_image, ((h - w) // 2, 0))
    return result


def pairwise_deterministic_shuffle(*args) -> Tuple:
    # Shuffle deterministically
    old_random_state = random.getstate()
    random.seed(0)
    temp = list(zip(args))
    random.shuffle(temp)
    random.setstate(old_random_state)
    return next(zip(*temp))

