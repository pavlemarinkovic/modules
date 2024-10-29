#!/usr/bin/env python3

import platform

import scanpy as sc
from threadpoolctl import threadpool_limits

threadpool_limits(int("${task.cpus}"))
sc.settings.n_jobs = int("${task.cpus}")


def format_yaml_like(data: dict, indent: int = 0) -> str:
    """Formats a dictionary to a YAML-like string.

    Args:
        data (dict): The dictionary to format.
        indent (int): The current indentation level.

    Returns:
        str: A string formatted as YAML.
    """
    yaml_str = ""
    for key, value in data.items():
        spaces = "  " * indent
        if isinstance(value, dict):
            yaml_str += f"{spaces}{key}:\\n{format_yaml_like(value, indent + 1)}"
        else:
            yaml_str += f"{spaces}{key}: {value}\\n"
    return yaml_str


adata = sc.read_h5ad("${h5ad}")
prefix = "${prefix}"
use_gpu = "${task.ext.use_gpu}" == "true"

if use_gpu:
    import cupy as cp
    import rapids_singlecell as rsc
    import rmm
    from rmm.allocators.cupy import rmm_cupy_allocator

    rmm.reinitialize(
        managed_memory=True,
        pool_allocator=False,
    )
    cp.cuda.set_allocator(rmm_cupy_allocator)

    rsc.get.anndata_to_GPU(adata)
    rsc.pp.scrublet(adata, batch_key="batch")
    rsc.get.anndata_to_CPU(adata)
else:
    sc.pp.scrublet(adata, batch_key="batch")

df = adata.obs[["predicted_doublet"]]
df.columns = ["${prefix}"]
df.to_pickle("${prefix}.pkl")

adata = adata[~adata.obs["predicted_doublet"]].copy()

adata.write_h5ad(f"{prefix}.h5ad")

# Versions

versions = {"${task.process}": {"python": platform.python_version(), "scanpy": sc.__version__}}

with open("versions.yml", "w") as f:
    f.write(format_yaml_like(versions))
