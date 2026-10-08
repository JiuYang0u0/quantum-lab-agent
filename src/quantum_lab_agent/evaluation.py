"""Post-run checks only; never choose tools or inject artifact IDs into the agent."""
from .runtime import render_report
from .schemas import validate_tool

# Freeze this evaluation's requested contract, independently of future schema defaults.
TRAINING_CONTRACT = {"architecture": "mlp", "epochs": 1, "patience": 1, "batch_size": 32,
                     "hidden_size": 8, "learning_rate": 0.001, "seed": 123,
                     "device": "cpu", "threads": 1}


def assess(export):
    dataset = checkpoint = comparison = None
    chain_ok = False
    sampled, trained = {}, {}
    reports, jobs, failures, steps, calls = [], {}, [], [], []
    pending = None
    status = "unknown"
    finish = None
    interpretation_status = "not_requested"
    for event in export["events"]:
        kind, data = event["kind"], event["data"]
        if kind == "model_metadata":
            steps.append(data)
        elif kind == "tool_call":
            pending = data
            calls.append({"step": len(steps), **data})
        elif kind == "tool_error":
            failures.append(data["error"])
            pending = None
        elif kind == "job":
            jobs[data["id"]] = {"step": len(steps), **{
                k: data.get(k) for k in ("id", "kind", "status", "artifact_id")}}
        elif kind == "finish":
            status = data["status"]
            finish = data
        elif kind == "interpretation_finish":
            interpretation_status = data["status"]
        elif kind == "tool_result" and pending and pending["tool"] == data["tool"]:
            name, result = data["tool"], data["result"]
            try:
                args = validate_tool(name, pending["args"])
                if name == "qec_sample":
                    dataset = result["artifact_id"]
                    checkpoint = comparison = None
                    chain_ok = False
                    sampled[dataset] = (args["sampling"] == {"train_shots": 64, "validation_shots": 16, "test_shots": 32}
                                 and args["circuit"] == {"code": "repetition", "distance": 3,
                                                        "rounds": 1, "p": 0.03, "seed": 42})
                elif name == "qec_train":
                    dataset = args["dataset_id"]
                    checkpoint = result["artifact_id"]
                    comparison = None
                    chain_ok = False
                    # Capture the dataset and its validity at training time; never
                    # carry a global train_ok flag across newly sampled artifacts.
                    trained[checkpoint] = (dataset, sampled.get(dataset, False)
                                           and args["training"] == TRAINING_CONTRACT)
                elif name in ("qec_compare", "qec_read_report"):
                    render_report(result)
                    if result["results"]:
                        reports.append(result)
                    if name == "qec_compare":
                        dataset = args["dataset_id"]
                        checkpoint = args["checkpoint_ids"][0] if len(args["checkpoint_ids"]) == 1 else None
                        comparison = result["artifact_id"]
                        rows = result["results"]
                        chain_ok = (sampled.get(dataset, False)
                                    and trained.get(checkpoint) == (dataset, True)
                                    and result["dataset_id"] == dataset
                                    and {r["decoder"] for r in rows} == {"mwpm", "lookup", "mlp"}
                                    and all(r["shots"] == 32 for r in rows)
                                    and any(r["decoder"] == "mlp" and r.get("checkpoint_id") == checkpoint
                                            for r in rows))
            except (KeyError, TypeError, ValueError):
                failures.append("invalid_evidence")
            pending = None
    classifications = []
    if failures:
        classifications.append("tool_or_evidence_error")
    if any(s.get("finish_reason") == "length" for s in steps):
        classifications.append("completion_token_limit")
    if status in ("step_budget", "tool_budget", "time_budget", "provider_error", "no_tool_calls", "report_goal_unmet"):
        classifications.append(status)
    if not chain_ok:
        classifications.append("incomplete_or_invalid_artifact_chain")
    if not reports:
        classifications.append("no_grounded_report")
    report = next((r for r in reports if r["artifact_id"] == comparison), None)
    assessment = {"run_id": export["run_id"], "task_success": bool(chain_ok and not failures),
            "termination_status": status, "report_produced": bool(reports),
            "failure_classifications": classifications, "tool_errors": failures,
            "dataset_id": dataset, "checkpoint_id": checkpoint, "comparison_id": comparison,
            "steps": steps, "tool_calls": calls, "jobs": list(jobs.values()),
            "numeric_provenance": [{**r, "source": f"{report['artifact_id']}#{r['prediction_key']}",
                                    "dataset_id": report["dataset_id"]}
                                   for r in report["results"]] if report else []}
    # Preserve the exact legacy assessment schema for original historical traces.
    if finish and "termination_source" in finish:
        assessment.update(termination_source=finish["termination_source"],
                          task_completion=finish["task_completion"],
                          model_stop_observed=any(s.get("finish_reason") == "stop" for s in steps),
                          interpretation_status=interpretation_status)
    return assessment
