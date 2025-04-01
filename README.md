# Running `snakemake` on Euler

## Installing snakemake

Install [mamba](https://github.com/conda-forge/miniforge?tab=readme-ov-file#install)

Version 8
```
mamba create -n snake8 -c conda-forge -c bioconda python=3.12 snakemake=8
```

Version 7
```
mamba create -n snake7 -c conda-forge -c bioconda python=3.12 snakemake=7.32.4
```

## Running snakemake


Internally, there are some changes to the profiles, so these currently are not identical in their operation.

Both require cloning this repository to your home config

```
mkdir -p ~/.config
git clone https://github.com/AnimalGenomicsETH/euler_profiles ~/.config/snakemake
```

### Version 8

We also need to install (via conda/mamba or pip) the `snakemake-executor-plugin-slurm`.
We can then run

```
snakemake --profile "slurm/v8" -n
```

Note, the profile has recently been updated to include the `--executor slurm` directive within the profile, so we no longer need to set it manually on the command line.

The main differences are the logging will be put in a hidden folder `.snakemake/slurm_logs/rule_{wildcards}/<SLURM_JOB_ID>.log`.
Currently this is for both stderr and stdout.

We also are a bit more restricted on the resource names, so

|    v7    |       v8       |
|----------|----------------|
| walltime |    runtime     |
|  mem_mb  | mem_mb_per_cpu |

The "disk_scratch" resource has technically been deprecated for a while, although should be requestable via "disk_mb" if needed.

The job name is also the full snakemake command, so `myjobs` looks a lot less pretty currently.

There is also something strange about how the "jobstep" works with SLURM through the executor, which prevents joining via interactive jobs.

### Version 7

```
snakemake --profile "slurm/full" -n
```

The logging should be put in a folder called `logs/<rule>/{wildcards}-{time}.out/err` with the stdout and stdrr logged separately.

#### Using `screen`

Snakemake often needs to run for a long time while the workflow completes.
It is easier to use `screen` and let a process run in the background (and persist after logging out)!

You can always log back in to the same head node and reconnect to your screen with `screen -r` (or `screen -r <ID>` if you have multiple screens active).
