from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pydoc import locate
from typing import Type

from torch import nn
from torch.utils.data.dataloader import DataLoader
from data.abstract_classes import AbstractDataset
from models.abstract_model import AbstractI2I
from models.ccgan import LabelEmbedding
from util.enums import DataSplit
from util.object_loader import build_from_yaml, load_yaml
import os
import torch

from util.pytorch_utils import seed_worker, set_seeds


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("--checkpoint_dir", type=str, required=True)
    parser.add_argument("--resume_from", type=int, required=True)
    parser.add_argument("--run_name", type=str, required=True)
    parser.add_argument("--args_file", type=str, required=True)
    parser.add_argument("--data_config", type=str, required=True)
    parser.add_argument("--batch_size", type=int, required=True)
    parser.add_argument("--n_workers", type=int, required=True)
    return parser.parse_args()


def eval(args: Namespace):
    checkpoint_dir = os.path.join(args.checkpoint_dir, args.run_name)
    hyperparams = load_yaml(os.path.join(checkpoint_dir, "hyperparams.yaml"))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    dataset: AbstractDataset = build_from_yaml(args.data_config)
    dataset.set_mode(DataSplit.TEST)
    data_shape = dataset.data_shape()
    if args.cyclical:
        data_shape.y_dim = 2
    if args.embed_generator:
        embedding = LabelEmbedding(args.ccgan_embedding_dim, n_labels=data_shape.y_dim)
        embedding.load_state_dict(torch.load(args.ccgan_embedding_file)())
        embedding.to(device)
        embedding.eval()
        embedding = nn.DataParallel(embedding)
    model_class: Type = locate(args.model)
    model: AbstractI2I = model_class(
        data_shape=data_shape, device=device, **hyperparams
    )
    model.load_checkpoint(args.resume_from, args.checkpoint_dir)
    model.to(device)
    model.set_eval()

    def transform_labels(y):
        with torch.no_grad():
            return embedding(y).detach() if args.embed_generator else y

    with torch.no_grad():
        evaluation = dataset.test_model(
            model.module.generator,
            args.batch_size,
            device,
            transform_labels,
        )
    with open(os.path.join(checkpoint_dir, "test_results.txt")) as f:
        f.write(str(evaluation))
        print(evaluation)


if __name__ == "__main__":
    args = parse_args()
    args_file = load_yaml(args.args_file)
    model_hyperparams = load_yaml(args.model_hyperparams)
    args = Namespace(**{**args_file, **model_hyperparams, **vars(args)})
    set_seeds(seed=0)
    # Always run in DataParallel. Should be fast enough anyways.
    eval(args)
