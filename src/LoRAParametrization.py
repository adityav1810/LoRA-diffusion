"CS7180 Advanced Perception  12/13/2023   Anirudh Muthuswamy, Gugan Kathiresan, Aditya Varshney"

from functools import partial
import math
import torch
import torch.nn.utils.parametrize as parametrize
from torch import nn

#The following class defines lora parameterizations for each layer in the model defined 
#by the nn.module class in pytorch

class LoRAParametrization(nn.Module):
    def __init__(self, fan_in, fan_out, fan_in_fan_out=False, rank=4, lora_dropout_p=0.0, lora_alpha=1):
        super().__init__()
        # if weight is stored as (fan_out, fan_in), the memory layout of A & B follows (W + BA)x
        # otherwise, it's x(W + AB). This allows us to tie the weights between linear layers and embeddings

        self.swap = (lambda x: (x[1], x[0])) if fan_in_fan_out else (lambda x: x)
        self.lora_A = nn.Parameter(torch.zeros(self.swap((rank, fan_in))))
        self.lora_B = nn.Parameter(torch.zeros(self.swap((fan_out, rank))))
        nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))
        self.lora_alpha, self.rank = lora_alpha, rank
        self.scaling = lora_alpha / rank
        self.lora_dropout = nn.Dropout(p=lora_dropout_p) if lora_dropout_p > 0 else lambda x: x
        self.dropout_fn = self._dropout if lora_dropout_p > 0 else lambda x: x
        self.register_buffer("lora_dropout_mask", torch.ones(self.swap((1, fan_in)), dtype=self.lora_A.dtype))
        self.forward_fn = self.lora_forward

    def _dropout(self, A):
        # to mimic the original implementation: A @ dropout(x), we do (A * dropout(ones)) @ x
        return A * self.lora_dropout(self.lora_dropout_mask)

    def lora_forward(self, X):
        return X + torch.matmul(*self.swap((self.lora_B, self.dropout_fn(self.lora_A)))).view(X.shape) * self.scaling

    def forward(self, X):
        return self.forward_fn(X)

    def disable_lora(self):
        self.forward_fn = lambda x: x

    def enable_lora(self):
        self.forward_fn = self.lora_forward

    @classmethod
    def from_linear(cls, layer, rank=4, lora_dropout_p=0.0, lora_alpha=1):
        fan_out, fan_in = layer.weight.shape
        return cls(
            fan_in, fan_out, fan_in_fan_out=False, rank=rank, lora_dropout_p=lora_dropout_p, lora_alpha=lora_alpha
        )

    @classmethod
    def from_conv2d(cls, layer, rank=4, lora_dropout_p=0.0, lora_alpha=1):
        fan_out, fan_in = layer.weight.view(layer.weight.shape[0], -1).shape
        return cls(
            fan_in, fan_out, fan_in_fan_out=False, rank=rank, lora_dropout_p=lora_dropout_p, lora_alpha=lora_alpha
        )


default_lora_config = {
    nn.Conv2d: {
        "weight": partial(LoRAParametrization.from_conv2d, rank=4),
    },
    nn.Linear: {
        "weight": partial(LoRAParametrization.from_linear, rank=4),
    },
}


def apply_lora(layer, register=True, merge=False, lora_config=default_lora_config):
    """add lora parametrization to a layer, designed to be used with model.apply"""
    # print("in apply_lora function: ", layer)
    if register:
        if type(layer) in lora_config:
            for attr_name, parametrization in lora_config[type(layer)].items():
                parametrize.register_parametrization(layer, attr_name, parametrization(layer))
    # else:  # this will remove all parametrizations, use with caution
    #     if hasattr(layer, "parametrizations"):
    #         for attr_name in layer.parametrizations.keys():
    #             parametrize.remove_parametrizations(layer, attr_name, leave_parametrized=merge)


def add_lora(model, lora_config=default_lora_config):
    """add lora parametrization to all layers in a model. Calling it twice will add lora twice"""
    model.apply(partial(apply_lora, lora_config=lora_config))

def merge_lora(model):
    """merge lora parametrization to all layers in a model. This will remove all parametrization"""
    model.apply(partial(apply_lora, register=False, merge=True))


def remove_lora(model):
    """remove lora parametrization to all layers in a model. This will remove all parametrization"""
    model.apply(partial(apply_lora, register=False, merge=False))

def apply_to_lora(fn):
    """apply a function to LoRAParametrization layers, designed to be used with model.apply"""

    def apply_fn(layer):
        if isinstance(layer, LoRAParametrization):
            fn(layer)

    return apply_fn


enable_lora = lambda model: model.apply(apply_to_lora(lambda x: x.enable_lora()))
disable_lora = lambda model: model.apply(apply_to_lora(lambda x: x.disable_lora()))


# ------------------- helper function for collecting parameters for training/saving -------------------


def name_is_lora(name):
    return (
        len(name.split(".")) >= 4
        and (name.split(".")[-4]) == "parametrizations"
        and name.split(".")[-1] in ["lora_A", "lora_B"]
    )


def name_is_bias(name):
    return name.split(".")[-1] == "bias"


def get_params_by_name(model, print_shapes=False, name_filter=None):
    for n, p in model.named_parameters():
        # print('n: ',n,' p: ',p)
        if name_filter is None or name_filter(n):
            if print_shapes:
                print(n, p.shape)
            yield p


def get_lora_params(model, print_shapes=False):
    return get_params_by_name(model, print_shapes=print_shapes, name_filter=name_is_lora)


def get_bias_params(model, print_shapes=False):
    return get_params_by_name(model, print_shapes=print_shapes, name_filter=name_is_bias)


def get_lora_state_dict(model):
    return {k: v for k, v in model.state_dict().items() if name_is_lora(k)}


# ------------------- helper function for inferencing with multiple lora -------------------


def _prepare_for_multiple_lora(lora_layer):
    lora_layer.lora_As = []
    lora_layer.lora_Bs = []


def _append_lora(lora_layer):
    lora_layer.lora_As.append(nn.Parameter(lora_layer.lora_A.clone()))
    lora_layer.lora_Bs.append(nn.Parameter(lora_layer.lora_B.clone()))


def load_multiple_lora(model, lora_state_dicts):
    model.apply(apply_to_lora(_prepare_for_multiple_lora))
    for state_dict in lora_state_dicts:
        _ = model.load_state_dict(state_dict, strict=False)
        model.apply(apply_to_lora(_append_lora))
    return model


def _select_lora(lora_layer, index):
    lora_layer.lora_A = lora_layer.lora_As[index]
    lora_layer.lora_B = lora_layer.lora_Bs[index]


def select_lora(model, index):
    model.apply(apply_to_lora(lambda x: _select_lora(x, index)))
    return model


# ------------------- helper function for tying and untieing weights -------------------


def tie_weights(linear: nn.Linear, embedding: nn.Embedding):
    """tie the weights of the linear layer and the embedding layer both with the same lora"""
    # this line below is optional if the original is already tied
    embedding.parametrizations.weight.original = linear.parametrizations.weight.original
    embedding.parametrizations.weight[0].lora_A = linear.parametrizations.weight[0].lora_B
    embedding.parametrizations.weight[0].lora_B = linear.parametrizations.weight[0].lora_A


def untie_weights(linear: nn.Linear, embedding: nn.Embedding):
    """untie the weights of the linear layer and the embedding layer"""
    embedding.parametrizations.weight.original = nn.Parameter(embedding.weight.original.clone())
    embedding.parametrizations.weight[0].lora_A = nn.Parameter(embedding.parametrizations.weight[0].lora_A.clone())
    embedding.parametrizations.weight[0].lora_B = nn.Parameter(embedding.parametrizations.weight[0].lora_B.clone())
