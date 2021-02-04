import io
import os
from typing import Optional, Union

import torch

from pytorch_lightning import LightningModule
from pytorch_lightning.plugins.training_type.single_device import SingleDevicePlugin
from pytorch_lightning.plugins.training_type.utils import on_colab_kaggle
from pytorch_lightning.utilities import _TPU_AVAILABLE, rank_zero_warn

if _TPU_AVAILABLE:
    import torch_xla
    import torch_xla.core.xla_model as xm


class SingleTPUPlugin(SingleDevicePlugin):

    def __init__(self, device: Union[torch.device, int]):
        if isinstance(device, int):
            device = xm.xla_device(device)
        super().__init__(device)

        self.tpu_local_core_rank = 0
        self.tpu_global_core_rank = 0

    def on_tpu(self) -> bool:
        return True

    def model_to_device(self) -> None:
        self._model.to(self.root_device)

    def pre_training(self) -> None:
        if isinstance(self.device, int):
            self.device = xm.xla_device(self.device)

        self.tpu_local_core_rank = xm.get_local_ordinal()
        self.tpu_global_core_rank = xm.get_ordinal()

    def post_training(self) -> None:
        model = self.lightning_module

        if on_colab_kaggle():
            rank_zero_warn("cleaning up... please do not interrupt")
            self.save_spawn_weights(model)

    def save_spawn_weights(self, model: LightningModule) -> Optional[str]:
        """
        Dump a temporary checkpoint after ddp ends to get weights out of the process
        """
        path = os.path.join(model.trainer.default_root_dir, "__temp_weight_distributed_end.ckpt")
        model.trainer.save_checkpoint(path)
        return path
