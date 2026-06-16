"""Unit tests for submission groups"""

import copy

from jade.extensions.generic_command import GenericCommandInputs
from jade.extensions.generic_command import GenericCommandConfiguration
from jade.hpc.common import HpcType
from jade.jobs.job_configuration_factory import create_config_from_file
from jade.models import SubmissionGroup, SubmitterParams
from jade.test_common import FAKE_HPC_CONFIG
from jade.utils.run_command import check_run_command, run_command
from jade.utils.utils import load_data


SUBMIT_JOBS = "jade submit-jobs -R none"


def test_submission_groups(tmp_path):
    config = create_config(tmp_path)
    config_file = tmp_path / "test-config.json"
    config.dump(str(config_file))

    output = tmp_path / "test-output"
    cmd = f"{SUBMIT_JOBS} {config_file} --output={output} -h {FAKE_HPC_CONFIG} -p 0.1"
    check_run_command(cmd)

    config_batch_files = list(output.glob("config_batch*.json"))
    assert len(config_batch_files) == 3
    batch1 = load_data(output / "config_batch_1.json")
    assert len(batch1["jobs"]) == 3
    batch2 = load_data(output / "config_batch_2.json")
    assert len(batch2["jobs"]) == 1
    assert batch2["jobs"][0]["job_id"] == 4
    batch3 = load_data(output / "config_batch_3.json")
    assert len(batch3["jobs"]) == 1
    assert batch3["jobs"][0]["job_id"] == 5


def test_submission_groups_duplicate_name(tmp_path):
    config = create_config(tmp_path)
    config.submission_groups[0].name = config.submission_groups[1].name
    config_file = tmp_path / "test-config.json"
    config.dump(str(config_file))
    output = tmp_path / "test-output"
    cmd = f"{SUBMIT_JOBS} {config_file} --output={output} -h {FAKE_HPC_CONFIG} --dry-run"
    assert run_command(cmd) != 0


def test_submission_groups_mixed_hpc_types(tmp_path):
    config = create_config(tmp_path)
    config.submission_groups[0].submitter_params.hpc_config.hpc_type = HpcType.SLURM
    config_file = tmp_path / "test-config.json"
    config.dump(str(config_file))
    output = tmp_path / "test-output"
    cmd = f"{SUBMIT_JOBS} {config_file} --output={output} -h {FAKE_HPC_CONFIG} --dry-run"
    assert run_command(cmd) != 0


def test_submission_groups_mixed_max_nodes(tmp_path):
    config = create_config(tmp_path)
    config.submission_groups[0].submitter_params.max_nodes = 5
    config_file = tmp_path / "test-config.json"
    config.dump(str(config_file))
    output = tmp_path / "test-output"
    cmd = f"{SUBMIT_JOBS} {config_file} --output={output} -h {FAKE_HPC_CONFIG} --dry-run"
    assert run_command(cmd) != 0


def test_submission_groups_per_node_setup(tmp_path):
    # TODO: this test is no longer in the right place. Belongs in file testing job_config.
    config = create_config(tmp_path)
    config.node_setup_command = "node_setup.sh"
    config.node_teardown_command = "node_teardown.sh"
    config_file = tmp_path / "test-config.json"
    config.dump(str(config_file))
    output = tmp_path / "test-output"
    cmd = f"{SUBMIT_JOBS} {config_file} --output={output} -h {FAKE_HPC_CONFIG} --dry-run"
    check_run_command(cmd)
    config = create_config_from_file(output / "config_batch_2.json")
    assert config.node_setup_command == "node_setup.sh"
    assert config.node_teardown_command == "node_teardown.sh"


def create_config(tmp_path):
    num_commands = 5
    commands = ['echo "hello world"'] * num_commands
    inputs_file = tmp_path / "test-inputs.txt"
    with open(inputs_file, "w") as f_out:
        for command in commands:
            f_out.write(command + "\n")

    inputs = GenericCommandInputs(str(inputs_file))
    config = GenericCommandConfiguration(job_inputs=inputs)
    jobs = list(inputs.iter_jobs())
    for i, job_param in enumerate(jobs):
        if i < 3:
            job_param.submission_group = "group1"
        else:
            job_param.submission_group = "group2"
        config.add_job(job_param)

    hpc_config1 = load_data(FAKE_HPC_CONFIG)
    hpc_config2 = copy.deepcopy(hpc_config1)
    hpc_config1["hpc"]["walltime"] = "1:00:00"
    hpc_config2["hpc"]["walltime"] = "5:00:00"
    params1 = SubmitterParams(hpc_config=hpc_config1, per_node_batch_size=3)
    params2 = SubmitterParams(hpc_config=hpc_config2, per_node_batch_size=1)
    group1 = SubmissionGroup(name="group1", submitter_params=params1)
    group2 = SubmissionGroup(name="group2", submitter_params=params2)
    config.append_submission_group(group1)
    config.append_submission_group(group2)
    return config
