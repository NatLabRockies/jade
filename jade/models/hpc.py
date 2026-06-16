"""Models for HPC configurations"""

import re
from typing import Optional, Union, List

from pydantic import Field, field_validator, model_validator

from jade.hpc.common import HpcType
from jade.models.base import JadeBaseModel


class SlurmConfig(JadeBaseModel):
    """Defines config options for the SLURM queueing system."""

    account: str = Field(
        title="account",
        description="Project account to use",
    )
    partition: Optional[str] = Field(
        title="partition",
        description="HPC partition on which to submit",
        default=None,
    )
    reservation: Optional[str] = Field(
        title="reservation",
        description="HPC reservation on which to submit",
        default=None,
    )
    qos: Optional[str] = Field(
        title="qos",
        description="Set to high to get faster node allocations at twice the cost",
        default=None,
    )
    walltime: str = Field(
        title="walltime",
        description="Maximum time allocated to each node",
        default="4:00:00",
    )
    gres: Optional[str] = Field(
        title="gpu",
        description="Request nodes that have at least this number of GPUs. Ex: 'gpu:2'",
        default=None,
    )
    mem: Optional[str] = Field(
        title="mem",
        description="Request nodes that have at least this amount of memory",
        default=None,
    )
    tmp: Optional[str] = Field(
        title="tmp",
        description="Request nodes that have at least this amount of storage scratch space",
        default=None,
    )
    nodes: Optional[int] = Field(
        title="nodes",
        description="Number of nodes to use for each job",
        default=None,
    )
    ntasks: Optional[int] = Field(
        title="ntasks",
        description="Number of tasks per job (nodes is not required if this is provided)",
        default=None,
    )
    ntasks_per_node: Optional[int] = Field(
        title="ntasks_per_node",
        description="Number of tasks per job (max in number of CPUs)",
        default=None,
    )

    @field_validator("gres")
    @classmethod
    def check_gpus(cls, gres):
        if gres is None:
            return gres
        if re.search(r"^gpu:(\d+)$", gres) is None:
            raise ValueError(
                "gres value must follow the format 'gpu:N' where N is the number of required GPUs"
            )
        return gres

    @model_validator(mode="before")
    @classmethod
    def handle_allocation(cls, values):
        if isinstance(values, dict) and "allocation" in values:
            values["account"] = values.pop("allocation")
        return values

    @model_validator(mode="after")
    def handle_nodes_and_tasks(self):
        if self.nodes is None and self.ntasks is None and self.ntasks_per_node is None:
            self.nodes = 1
        return self


class FakeHpcConfig(JadeBaseModel):
    """Defines config options for the fake queueing system."""

    # Keep this required so that Pydantic can differentiate the models.
    walltime: str = Field(
        title="walltime",
        description="Maximum time allocated to each node",
    )


class LocalHpcConfig(JadeBaseModel):
    """Defines config options when there is no HPC."""


class HpcConfig(JadeBaseModel):
    """Defines config options for the HPC."""

    hpc_type: HpcType = Field(
        title="hpc_type",
        description="Type of HPC queueing system (such as 'slurm')",
    )
    job_prefix: str = Field(
        title="job_prefix",
        description="Prefix added to each HPC job name",
        default="job",
    )
    hpc: Union[SlurmConfig, FakeHpcConfig, LocalHpcConfig] = Field(
        title="hpc",
        description="Interface-specific config options",
    )

    @field_validator("hpc", mode="before")
    @classmethod
    def assign_hpc(cls, value, info):
        if isinstance(value, JadeBaseModel):
            return value

        hpc_type = info.data.get("hpc_type")
        if hpc_type is None:
            raise ValueError("'hpc_type' is required to validate 'hpc'")
        if hpc_type == HpcType.SLURM:
            return SlurmConfig(**value)
        elif hpc_type == HpcType.FAKE:
            return FakeHpcConfig(**value)
        elif hpc_type == HpcType.LOCAL:
            return LocalHpcConfig()
        raise ValueError(f"Unsupported: {hpc_type}")

    def get_num_gpus(self):
        """Return the number of GPUs specified by the config.

        Returns
        -------
        int

        """
        if isinstance(self.hpc, SlurmConfig) and self.hpc.gres is not None:
            return int(self.hpc.gres.split(":")[1])
        return 0
