"""
Unit tests for resubmitting failed and missing jobs
"""

from jade.common import RESULTS_FILE
from jade.extensions.generic_command import GenericCommandInputs
from jade.extensions.generic_command import GenericCommandConfiguration
from jade.jobs.results_aggregator import ResultsAggregator
from jade.result import Result, ResultsSummary
from jade.test_common import FAKE_HPC_CONFIG
from jade.utils.subprocess_manager import run_command, check_run_command
from jade.utils.utils import load_data, dump_data


SUBMIT_JOBS = f"jade submit-jobs -h {FAKE_HPC_CONFIG} -R none"
RESUBMIT_JOBS = "jade resubmit-jobs"
WAIT = "jade wait"
NUM_COMMANDS = 5


def _create_config(tmp_path):
    commands = ['echo "hello world"'] * NUM_COMMANDS
    inputs_file = tmp_path / "test-inputs.txt"
    with open(inputs_file, "w") as f_out:
        for command in commands:
            f_out.write(command + "\n")

    inputs = GenericCommandInputs(str(inputs_file))
    config = GenericCommandConfiguration.auto_config(inputs)
    config_file = tmp_path / "test-config.json"
    config.dump(str(config_file))
    return config_file


def test_resubmit_successful(tmp_path):
    config_file = _create_config(tmp_path)
    output = tmp_path / "test-output"
    sg_file = tmp_path / "test-submission-groups.json"
    cmd = f"{SUBMIT_JOBS} {config_file} --output={output} -p 0.1"
    check_run_command(cmd)
    check_run_command(f"{WAIT} --output={output} -p 0.1 -t2")
    summary = ResultsSummary(str(output))
    assert len(summary.get_failed_results()) == 0
    assert len(summary.get_successful_results()) == NUM_COMMANDS

    check_run_command(f"jade config save-submission-groups {output} -c {sg_file}")
    groups = load_data(sg_file)
    assert groups[0]["submitter_params"]["per_node_batch_size"] > NUM_COMMANDS
    groups[0]["submitter_params"]["per_node_batch_size"] = NUM_COMMANDS
    dump_data(groups, sg_file)

    check_run_command(f"{RESUBMIT_JOBS} {output} -s {sg_file} --successful")
    check_run_command(f"{WAIT} --output={output} -p 0.1")
    summary = ResultsSummary(str(output))
    assert len(summary.get_failed_results()) == 0
    assert len(summary.get_successful_results()) == NUM_COMMANDS

    check_run_command(f"jade config save-submission-groups {output} --force -c {sg_file}")
    groups = load_data(sg_file)
    assert groups[0]["submitter_params"]["per_node_batch_size"] == NUM_COMMANDS


def test_resubmit_failed(tmp_path):
    config_file = _create_config(tmp_path)
    output = tmp_path / "test-output"
    cmd = f"{SUBMIT_JOBS} {config_file} --output={output} -p 0.1"
    ret = run_command(cmd)
    assert ret == 0
    ret = run_command(f"{WAIT} --output={output} -p 0.1")
    assert ret == 0

    agg = ResultsAggregator.load(str(output))
    results = agg.get_results_unsafe()
    assert results
    for result in results:
        assert result.return_code == 0
    x = results[0]
    results[0] = Result(x.name, 1, x.status, x.exec_time_s, x.completion_time, hpc_job_id=None)
    agg._write_results(results)

    results_filename = output / RESULTS_FILE
    final_results = load_data(results_filename)
    final_results["results"][0]["return_code"] = 1
    final_results["results_summary"]["num_failed"] = 1
    final_results["results_summary"]["num_successful"] -= 1
    dump_data(final_results, results_filename)

    summary = ResultsSummary(str(output))
    assert summary.get_failed_results()[0].name == "1"

    ret = run_command(f"{RESUBMIT_JOBS} {output}")
    assert ret == 0
    ret = run_command(f"{WAIT} --output={output} -p 0.1")
    assert ret == 0

    summary = ResultsSummary(str(output))
    assert len(summary.get_successful_results()) == NUM_COMMANDS


def test_resubmit_missing(tmp_path):
    config_file = _create_config(tmp_path)
    output = tmp_path / "test-output"
    cmd = f"{SUBMIT_JOBS} {config_file} --output={output} -p 0.1"
    ret = run_command(cmd)
    assert ret == 0
    ret = run_command(f"{WAIT} --output={output} -p 0.1")
    assert ret == 0

    agg = ResultsAggregator.load(str(output))
    results = agg.get_results_unsafe()
    assert results
    for result in results:
        assert result.return_code == 0
    results.pop()
    agg._write_results(results)

    results_filename = output / RESULTS_FILE
    final_results = load_data(results_filename)
    missing = final_results["results"].pop()
    final_results["results_summary"]["num_missing"] = 1
    final_results["results_summary"]["num_successful"] -= 1
    final_results["missing_jobs"] = [missing["name"]]
    dump_data(final_results, results_filename)

    summary = ResultsSummary(str(output))
    assert len(summary.get_failed_results()) == 0
    assert len(summary.get_successful_results()) == NUM_COMMANDS - 1

    ret = run_command(f"{RESUBMIT_JOBS} {output}")
    assert ret == 0
    ret = run_command(f"{WAIT} --output={output} -p 0.1")
    assert ret == 0

    summary = ResultsSummary(str(output))
    assert len(summary.get_successful_results()) == NUM_COMMANDS


def test_resubmit_with_blocking_jobs(tmp_path):
    num_commands = 7
    commands = ['echo "hello world"'] * num_commands
    inputs_file = tmp_path / "test-inputs.txt"
    with open(inputs_file, "w") as f_out:
        for command in commands:
            f_out.write(command + "\n")

    inputs = GenericCommandInputs(str(inputs_file))
    config = GenericCommandConfiguration(job_inputs=inputs)
    jobs = list(inputs.iter_jobs())
    # Set an inefficient ordering to make sure the resubmit algorithm is recursive.
    for i, job_param in enumerate(jobs):
        if i == 3:
            job_param.blocked_by = set([5])
        elif i == 4:
            job_param.blocked_by = set([7])
        elif i == 6:
            job_param.blocked_by = set([6])
        config.add_job(job_param)
    config_file = tmp_path / "test-config.json"
    config.dump(str(config_file))
    output = tmp_path / "test-output"
    cmd = f"{SUBMIT_JOBS} {config_file} --output={output}"
    ret = run_command(cmd)
    assert ret == 0
    ret = run_command(f"{WAIT} --output={output} -p 0.1")
    assert ret == 0

    agg = ResultsAggregator.load(str(output))
    results = agg.get_results_unsafe()
    assert results
    for result in results:
        assert result.return_code == 0
    found = False
    for i, result in enumerate(results):
        if result.name == "7":
            results.pop(i)
            found = True
            break
    assert found
    agg._write_results(results)

    results_filename = output / RESULTS_FILE
    final_results = load_data(results_filename)
    missing = None
    for i, result in enumerate(final_results["results"]):
        if result["name"] == "7":
            missing = result
            final_results["results"].pop(i)
            break
    assert missing is not None
    final_results["results_summary"]["num_missing"] = 1
    final_results["results_summary"]["num_successful"] -= 1
    final_results["missing_jobs"] = [missing["name"]]
    dump_data(final_results, results_filename)

    summary = ResultsSummary(str(output))
    assert len(summary.get_failed_results()) == 0
    assert len(summary.get_successful_results()) == num_commands - 1
    first_batch = load_data(output / "config_batch_1.json")
    assert len(first_batch["jobs"]) == num_commands

    ret = run_command(f"{RESUBMIT_JOBS} {output}")
    assert ret == 0
    ret = run_command(f"{WAIT} --output={output} -p 0.1")
    assert ret == 0

    summary = ResultsSummary(str(output))
    assert len(summary.get_successful_results()) == num_commands

    second_batch_file = output / "config_batch_2.json"
    assert second_batch_file.exists()
    second_batch = load_data(second_batch_file)["jobs"]
    assert len(second_batch) == 3
