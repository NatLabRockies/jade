"""
Unit tests for adding blocked jobs.
"""

from jade.extensions.generic_command import GenericCommandInputs
from jade.extensions.generic_command import GenericCommandConfiguration
from jade.events import EventsSummary, EVENT_NAME_HPC_SUBMIT
from jade.test_common import FAKE_HPC_CONFIG
from jade.utils.subprocess_manager import run_command


SUBMIT_JOBS = "jade submit-jobs -R none"
WAIT = "jade wait"


def test_try_add_blocked_jobs(tmp_path):
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
        if i == num_commands - 1:
            job_param.blocked_by = set([1, 2, 3, 4])
        config.add_job(job_param)
    config_file = tmp_path / "test-config.json"
    config.dump(str(config_file))

    # Use a unique output directory per submission. The fake submitter spawns
    # detached background processes that can outlive 'jade wait', so reusing a
    # single directory across submissions allows a leftover process to collide
    # with a subsequent '--force' run and intermittently fail the test.
    for i, option in enumerate(("--try-add-blocked-jobs", "--no-try-add-blocked-jobs")):
        output = tmp_path / f"test-output-{i}"
        cmd = (
            f"{SUBMIT_JOBS} {config_file} --output={output} --force "
            f"-h {FAKE_HPC_CONFIG} -p 0.1 {option}"
        )
        ret = run_command(cmd)
        assert ret == 0
        ret = run_command(f"{WAIT} --output={output} -p 0.1")
        assert ret == 0
        events_summary = EventsSummary(str(output), preload=True)
        submit_events = events_summary.list_events(EVENT_NAME_HPC_SUBMIT)
        if option == "--try-add-blocked-jobs":
            assert len(submit_events) == 1
            event = submit_events[0]
            assert event.data["batch_size"] == num_commands
        else:
            assert len(submit_events) == 2
            event1 = submit_events[0]
            event2 = submit_events[1]
            assert event1.data["batch_size"] == num_commands - 1
            assert event2.data["batch_size"] == 1
