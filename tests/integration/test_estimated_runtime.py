import pytest

from jade.exceptions import ExecutionError
from jade.extensions.generic_command import GenericCommandInputs
from jade.extensions.generic_command import GenericCommandConfiguration
from jade.test_common import FAKE_HPC_CONFIG
from jade.utils.run_command import check_run_command
from jade.utils.utils import load_data


SUBMIT_JOBS = f"jade submit-jobs -h {FAKE_HPC_CONFIG} -R none"
WAIT = "jade wait"
NUM_COMMANDS = 100


def _create_config(tmp_path, job_too_long=False):
    commands = ['echo "hello world"'] * NUM_COMMANDS
    inputs_file = tmp_path / "test-inputs.txt"
    with open(inputs_file, "w") as f_out:
        for command in commands:
            f_out.write(command + "\n")

    inputs = GenericCommandInputs(str(inputs_file))
    config = GenericCommandConfiguration.auto_config(inputs, minutes_per_job=10)
    if job_too_long:
        for i, job in enumerate(config.iter_jobs()):
            if i == 1:
                job.estimated_run_minutes = 1000
                break
    config_file = tmp_path / "test-config.json"
    config.dump(str(config_file))
    return config_file


def test_estimated_run_time(tmp_path):
    # walltime is 240 minutes
    # 10-minute jobs
    # Each of 4 cores can each complete 24 jobs. 4 * 24 = 96 jobs
    # 100 jobs will take two batches.
    config_file = _create_config(tmp_path)
    output = tmp_path / "test-output"
    cmd = f"{SUBMIT_JOBS} {config_file} --output={output} -p 0.1 -t -n2 -q4"
    check_run_command(cmd)
    check_run_command(f"{WAIT} --output={output} -p 0.1 -t2")

    batch_config_1 = output / "config_batch_1.json"
    assert batch_config_1.exists()
    batch_config_2 = output / "config_batch_2.json"
    assert batch_config_2.exists()

    config1 = load_data(batch_config_1)
    assert len(config1["jobs"]) == 96
    config2 = load_data(batch_config_2)
    assert len(config2["jobs"]) == 4


def test_estimated_run_time_too_long(tmp_path):
    config_file = _create_config(tmp_path, job_too_long=True)
    output = tmp_path / "test-output"
    cmd = f"{SUBMIT_JOBS} {config_file} --output={output}"
    with pytest.raises(ExecutionError):
        check_run_command(cmd)
