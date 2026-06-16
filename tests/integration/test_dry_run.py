"""Unit tests for dry-run mode"""

from jade.extensions.generic_command import GenericCommandInputs
from jade.extensions.generic_command import GenericCommandConfiguration
from jade.test_common import SLURM_HPC_CONFIG
from jade.utils.run_command import check_run_command


NUM_COMMANDS = 5


def test_dry_run(tmp_path):
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
    cmd = f"jade submit-jobs --dry-run -h {SLURM_HPC_CONFIG} {config_file} --output={output}"
    check_run_command(cmd)
