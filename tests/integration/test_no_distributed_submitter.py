"""
Unit tests for disabling the distributed submitter
"""

import time

from jade.common import RESULTS_DIR
from jade.extensions.generic_command import GenericCommandInputs
from jade.extensions.generic_command import GenericCommandConfiguration
from jade.test_common import FAKE_HPC_CONFIG
from jade.utils.subprocess_manager import check_run_command


SUBMIT_JOBS = f"jade submit-jobs -h {FAKE_HPC_CONFIG} -R none"
TRY_SUBMIT_JOBS = "jade try-submit-jobs"
WAIT = "jade wait -p 0.1"
NUM_COMMANDS = 5


def test_no_distributed_submitter(tmp_path):
    commands = ['echo "hello world"'] * NUM_COMMANDS
    inputs_file = tmp_path / "test-inputs.txt"
    with open(inputs_file, "w") as f_out:
        for command in commands:
            f_out.write(command + "\n")

    inputs = GenericCommandInputs(str(inputs_file))
    config = GenericCommandConfiguration.auto_config(inputs)
    config_file = tmp_path / "test-config.json"
    config.dump(str(config_file))

    output = tmp_path / "test-output"
    cmd = f"{SUBMIT_JOBS} {config_file} --output={output} -p 0.1 -N --no-reports"
    check_run_command(cmd)

    results_file = output / RESULTS_DIR / "results_batch_1.csv"
    processed_results_file = output / "processed_results.csv"
    all_jobs_complete = False
    for _ in range(10):
        if results_file.exists():
            lines = results_file.read_text().splitlines()
            # The file has an extra line for the header.
            if len(lines) == NUM_COMMANDS + 1:
                all_jobs_complete = True
                break
        time.sleep(1)

    assert all_jobs_complete
    assert len(processed_results_file.read_text().splitlines()) == 1

    check_run_command(f"{TRY_SUBMIT_JOBS} {output}")
    check_run_command(f"{WAIT} --output={output} -p 0.1 -t2")
    assert len(processed_results_file.read_text().splitlines()) == NUM_COMMANDS + 1
    assert not results_file.exists()
