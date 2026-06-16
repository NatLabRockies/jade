"""
Unit tests for canceling jobs on failure
"""

from jade.extensions.generic_command import GenericCommandInputs
from jade.extensions.generic_command import GenericCommandConfiguration
from jade.result import ResultsSummary
from jade.test_common import FAKE_HPC_CONFIG
from jade.utils.subprocess_manager import run_command


SUBMIT_JOBS = f"jade submit-jobs -h {FAKE_HPC_CONFIG} -R periodic -r 1"
WAIT = "jade wait"


def _create_config(tmp_path):
    commands = [
        'echo "hello"',
        "ls invalid-path",
        'echo "hello"',
        'echo "hello"',
        'echo "hello"',
        'echo "hello"',
        'echo "hello"',
        'echo "hello"',
    ]
    inputs_file = tmp_path / "test-inputs.txt"
    with open(inputs_file, "w") as f_out:
        for command in commands:
            f_out.write(command + "\n")

    inputs = GenericCommandInputs(str(inputs_file))
    config = GenericCommandConfiguration.auto_config(inputs, cancel_on_blocking_job_failure=True)
    config.get_job("3").set_blocking_jobs(set([2]))
    config.get_job("4").set_blocking_jobs(set([3]))
    config.get_job("5").set_blocking_jobs(set([4]))
    config.get_job("6").set_blocking_jobs(set([5]))
    config.get_job("7").set_blocking_jobs(set([6]))
    config.get_job("8").set_blocking_jobs(set([7]))
    config_file = tmp_path / "test-config.json"
    config.dump(str(config_file))
    return config_file


def test_cancel_on_failure_detect_by_submitter(tmp_path):
    # HpcSubmitter handles the cancellation because the blocked job will be in the 2nd batch.
    config_file = _create_config(tmp_path)
    output = tmp_path / "test-output"
    cmd = f"{SUBMIT_JOBS} {config_file} --output={output} -n2 -b2"
    ret = run_command(cmd)
    assert ret == 0
    ret = run_command(f"{WAIT} --output={output} -p 0.1 -t 2")
    assert ret == 0

    summary = ResultsSummary(str(output))
    assert len(summary.get_successful_results()) == 1
    assert len(summary.get_failed_results()) == 1
    assert len(summary.get_canceled_results()) == 6
    results = summary.get_results_by_type()
    assert len(results["successful"]) == 1
    assert len(results["failed"]) == 1
    assert len(results["canceled"]) == 6


def test_cancel_on_failure_detect_by_runner(tmp_path):
    # JobRunner handles the cancellation in JobQueue because the blocked job is in the batch
    # along with the blocking job.
    config_file = _create_config(tmp_path)
    output = tmp_path / "test-output"
    cmd = f"{SUBMIT_JOBS} {config_file} --output={output} -n2 -b8"
    ret = run_command(cmd)
    assert ret == 0
    ret = run_command(f"{WAIT} --output={output} -p 0.1 -t 2")
    assert ret == 0

    summary = ResultsSummary(str(output))
    assert len(summary.get_successful_results()) == 1
    assert len(summary.get_failed_results()) == 1
    assert len(summary.get_canceled_results()) == 6
    results = summary.get_results_by_type()
    assert len(results["successful"]) == 1
    assert len(results["failed"]) == 1
    assert len(results["canceled"]) == 6
