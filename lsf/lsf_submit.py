#!/usr/bin/env python3
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Union, Optional
import datetime
from snakemake.utils import read_job_properties

sys.path.append(str(Path(__file__).parent.absolute()))
from OSLayer import OSLayer
from lsf_config import Config
#from memory_units import Unit, Memory

PathLike = Union[str, Path]


class BsubInvocationError(Exception):
    pass


class JobidNotFoundError(Exception):
    pass


class Submitter:
    def __init__(
        self,
        jobscript: PathLike,
        cluster_cmds: List[str] = None,
        #memory_units: Unit = Unit.MEGA,
        lsf_config: Optional[Config] = None,
    ):
        if cluster_cmds is None:
            cluster_cmds = []
        if lsf_config is None:
            lsf_config = Config()

        self._jobscript = jobscript
        self._cluster_cmd = " ".join(cluster_cmds)
        self._job_properties = read_job_properties(self._jobscript)
        self.random_string = OSLayer.get_uuid4_string()
        #self._memory_units = memory_units
        self.lsf_config = lsf_config

    @property
    def jobscript(self) -> str:
        return self._jobscript

    @property
    def job_properties(self) -> dict:
        return self._job_properties

    @property
    def cluster(self) -> dict:
        return self.job_properties.get("cluster", dict())

    @property
    def threads(self) -> int:
        return self.job_properties.get("threads", 1)

    @property
    def walltime(self) -> str:
        return self.resources.get("walltime", "4:00")
    
    @property
    def disk_scratch(self) -> int:
        return self.resources.get("disk_scratch",0)    

    @property
    def resources(self) -> dict:
        return self.job_properties.get("resources", dict())

    @property
    def mem_mb(self) -> int:
        return self.resources.get("mem_mb", self.cluster.get("mem_mb", 1024))
    
    @property
    def use_singularity(self) -> int:
        return self.resources.get("use_singularity",0)
    
    @property
    def use_AVX512(self) -> int:
        return self.resources.get("use_AVX512",0)

    #@property
    #def memory_units(self) -> Unit:
    #    return self._memory_units

    @property
    def resources_cmd(self) -> str:
        r_cmd = f'-M {self.mem_mb} -n {self.threads} ' \
                f'-R "rusage[mem={self.mem_mb}] span[hosts=1]" ' \
                f'-W {self.walltime}'
        if self.disk_scratch:
            r_cmd += f' -R "rusage[scratch={self.disk_scratch*1000/self.threads}]"'
        if self.use_singularity:
            r_cmd += ' -R singularity'
        if self.use_AVX512:
            r_cmd += ' -R "select[model==XeonGold_6140]"'
        return r_cmd
    
    @property
    def wildcards(self) -> dict:
        return self.job_properties.get("wildcards", dict())

    @property
    def wildcards_str(self) -> str:
        return (
            ".".join("{}-{}".format(k, v) for k, v in self.wildcards.items())
            or "unique"
        )

    @property
    def rule_name(self) -> str:
        if not self.is_group_jobtype:
            return self.job_properties.get("rule", "rule_name")
        return self.groupid

    @property
    def groupid(self) -> str:
        return self.job_properties.get("groupid", "group")

    @property
    def is_group_jobtype(self) -> bool:
        return self.job_properties.get("type", "") == "group"

    @property
    def jobname(self) -> str:
        if self.is_group_jobtype:
            return "{groupid}_{jobid}".format(groupid=self.groupid, jobid=self.jobid)
        return self.cluster.get(
            "jobname",
            "{rule_name}.{wildcards_str}".format(
                rule_name=self.rule_name, wildcards_str=self.wildcards_str
            ),
        )

    @property
    def jobid(self) -> str:
        if self.is_group_jobtype:
            return self.job_properties.get("jobid", "").split("-")[0]
        return str(self.job_properties.get("jobid"))

    @property
    def logdir(self) -> Path:
        project_logdir = Path(self.cluster.get("logdir", "logs"))
        return project_logdir / self.rule_name

    @property
    def outlog(self) -> Path:
        return self.logdir / f"{self.wildcards_str.replace('/','.slash.')}_{datetime.datetime.now().strftime('%Y%m%d%H%M')}.out"

    @property
    def errlog(self) -> Path:
        return self.logdir / f"{self.wildcards_str.replace('/','.slash.')}_{datetime.datetime.now().strftime('%Y%m%d%H%M')}.err"

    @property
    def jobinfo_cmd(self) -> str:
        return '-o "{out_log}" -e "{err_log}" -J "{jobname}"'.format(
            out_log=self.outlog, err_log=self.errlog, jobname=self.jobname
        )

    @property
    def queue(self) -> str:
        return self.cluster.get("queue", "")

    @property
    def queue_cmd(self) -> str:
        return "-q {}".format(self.queue) if self.queue else ""

    @property
    def rule_specific_params(self) -> str:
        return self.lsf_config.params_for_rule(self.rule_name)

    @property
    def cluster_cmd(self) -> str:
        return self._cluster_cmd

    @property
    def submit_cmd(self) -> str:
        params = [
            "bsub",
            self.resources_cmd,
            self.jobinfo_cmd,
            self.queue_cmd,
            self.cluster_cmd,
            self.rule_specific_params,
            self.jobscript,
        ]
        return " ".join(p for p in params if p)

    def _create_logdir(self):
        OSLayer.mkdir(self.logdir)

    def _remove_previous_logs(self):
        OSLayer.remove_file(self.outlog)
        OSLayer.remove_file(self.errlog)

    def _submit_cmd_and_get_external_job_id(self) -> int:
        output_stream, error_stream = OSLayer.run_process(self.submit_cmd)
        match = re.search(r"Job <(\d+)> is submitted", output_stream)
        jobid = match.group(1)
        return int(jobid)

    def _get_parameters_to_status_script(self, external_job_id: int) -> str:
        return "{external_job_id} {outlog}".format(
            external_job_id=external_job_id, outlog=self.outlog
        )

    def submit(self):
        self._create_logdir()
        self._remove_previous_logs()
        try:
            external_job_id = self._submit_cmd_and_get_external_job_id()
            parameters_to_status_script = self._get_parameters_to_status_script(
                external_job_id
            )
            OSLayer.print(parameters_to_status_script)
        except subprocess.CalledProcessError as error:
            raise BsubInvocationError(error)
        except AttributeError as error:
            raise JobidNotFoundError(error)


if __name__ == "__main__":
    workdir = Path().resolve()
    config_file = workdir / "lsf.yaml"
    if config_file.exists():
        with config_file.open() as stream:
            lsf_config = Config.from_stream(stream)
    else:
        lsf_config = Config()

    jobscript = sys.argv[-1]
    cluster_cmds = sys.argv[1:-1]
    #memory_units = Unit.from_suffix("MB")
    lsf_submit = Submitter(
        jobscript=jobscript,
        #memory_units=memory_units,
        lsf_config=lsf_config,
        cluster_cmds=cluster_cmds,
    )
    lsf_submit.submit()
