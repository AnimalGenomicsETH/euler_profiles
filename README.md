# Running `snakemake` on Euler

## Installation

### Installing snakemake

Due to filesystem issues with `conda`, it is better to install snakemake with `uv`.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

We can then create a virtual environment to later install snakemake in

```bash
uv venv --python 3.14 ~/.venvs/snakemake
```

And then we activate the venv and install `snakemake` through pip, as well as the slurm executor and fs plugins

```bash
source ~/.venvs/snakemake/bin/activate

uv pip install snakemake snakemake-executor-plugin-slurm snakemake-storage-plugin-fs
```

### Installing Euler profiles

We can then add the profiles in this repository to our path

```bash
mkdir -p ~/.config
git clone https://github.com/AnimalGenomicsETH/euler_profiles ~/.config/snakemake
```

The key file is "Euler/config.yaml", which specifies how snakemake should interact with the Euler HPC.


## Running snakemake

We can now run snakemake on Euler using


```bash
snakemake --profile "Euler"
```

Many of these features are targeted at a minumum snakemake version of 8.0.

## Defaults

 - Output slurm logs are written to "slurm_logs"

## Limitations

 - Using `conda` and `apptainer` at the same time requires CLI overriding
