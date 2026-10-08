"""Versioned, offline binding checks for the bounded sample/train/compare evidence.

The legacy evaluator remains a historical scientific assessment. This additional
gate verifies the serial native/execution/job transcript, not HTTP wire traffic
(the archived exporter did not record URLs or submission responses).
"""
import copy
import json

from pydantic import TypeAdapter

from .evaluation import assess
from .schemas import ID, validate_tool

NOISE_DEFAULTS = (
    "after_clifford_depolarization", "before_round_data_depolarization",
    "before_measure_flip_probability", "after_reset_flip_probability",
)
ENDPOINTS = {f"qec_{kind}": f"/api/jobs/{kind}" for kind in ("sample", "train", "compare")}


def normalize_request(name, request):
    """Accept B's explicit null noise overrides, but never discard nondefaults."""
    request = copy.deepcopy(request)
    if name == "qec_sample":
        for key in NOISE_DEFAULTS:
            if key in request.get("circuit", {}) and request["circuit"].pop(key) is not None:
                raise ValueError("nondefault service noise override")
    return validate_tool(name, request)


def bound_qec_execution(events):
    """Fail closed; return calls bound to every job poll and terminal result.

    Only one bounded chain is supported. Repeated polls are expected; repeated
    calls, job reuse, orphan events and events after termination are not.
    """
    pending, pairs, native_ids, job_ids, artifact_ids = [], [], set(), set(), set()
    active = None
    ended = False
    for event in events:
        kind, data = event["kind"], event["data"]
        if ended and kind in ("model", "tool_call", "intent", "job", "tool_result", "tool_error"):
            raise ValueError("execution after finish")
        if kind == "model":
            if pending or active:
                raise ValueError("model turn before completion")
            for call in data.get("tool_calls", []):
                identity = call["id"]
                if not isinstance(identity, str) or not identity or identity in native_ids:
                    raise ValueError("missing or duplicate native ID")
                native_ids.add(identity)
                if call.get("type") != "function":
                    raise ValueError("native call is not a function")
                name = call["function"]["name"]
                if name not in ENDPOINTS and name != "qec_read_report":
                    raise ValueError("tool outside bounded QEC chain")
                args = validate_tool(name, json.loads(call["function"]["arguments"]))
                pending.append((identity, name, args))
        elif kind == "tool_call":
            if active or not pending:
                raise ValueError("orphan or overlapping execution")
            identity, name, args = pending.pop(0)
            if name != data["tool"] or args != validate_tool(name, data["args"]):
                raise ValueError("native/executed arguments mismatch")
            active = {"native_id": identity, "tool": name, "args": args,
                      "endpoint": ENDPOINTS.get(name), "jobs": [], "intent": False}
        elif kind == "intent":
            if (not active or active["intent"] or active["jobs"]
                    or data["tool"] != active["tool"]
                    or validate_tool(data["tool"], data["args"]) != active["args"]):
                raise ValueError("orphan or mismatched intent")
            active["intent"] = True
        elif kind == "job":
            if not active or active["tool"] not in ENDPOINTS:
                raise ValueError("orphan job")
            name = active["tool"]
            identity = TypeAdapter(ID).validate_python(data["id"])
            if data["kind"] != name.removeprefix("qec_"):
                raise ValueError("wrong job endpoint kind")
            if normalize_request(name, data["request"]) != active["args"]:
                raise ValueError("executed/job request mismatch")
            jobs = active["jobs"]
            if jobs:
                if identity != jobs[0]["id"] or jobs[-1]["status"] == "succeeded":
                    raise ValueError("job identity or terminal ordering mismatch")
                if jobs[-1]["status"] == "running" and data["status"] == "queued":
                    raise ValueError("job status regressed")
            elif identity in job_ids:
                raise ValueError("reused job ID")
            job_ids.add(identity)
            if data["status"] not in ("queued", "running", "succeeded") or data.get("error"):
                raise ValueError("unsuccessful job")
            if data["status"] == "succeeded":
                TypeAdapter(ID).validate_python(data["artifact_id"])
            elif data.get("artifact_id") is not None:
                raise ValueError("nonterminal artifact")
            jobs.append(data)
        elif kind == "tool_result":
            if not active or active["tool"] != data["tool"]:
                raise ValueError("orphan or reordered result")
            result, name = data["result"], active["tool"]
            artifact = TypeAdapter(ID).validate_python(result["artifact_id"])
            if name in ENDPOINTS:
                jobs = active["jobs"]
                if not jobs or jobs[-1]["status"] != "succeeded":
                    raise ValueError("missing successful terminal job")
                if artifact != jobs[-1]["artifact_id"] or artifact in artifact_ids:
                    raise ValueError("result artifact mismatch or reuse")
                artifact_ids.add(artifact)
                if name != "qec_compare" and (result["job_id"] != jobs[-1]["id"]
                                               or result["status"] != "succeeded"):
                    raise ValueError("result job ID or success status mismatch")
            elif active["args"]["result_id"] != artifact:
                raise ValueError("read artifact mismatch")
            pairs.append({**active, "result": result})
            active = None
        elif kind == "tool_error":
            raise ValueError("tool error")
        elif kind == "finish":
            if active or pending:
                raise ValueError("finish before completion")
            ended = True
    if active or pending:
        raise ValueError("incomplete execution")
    names = [p["tool"] for p in pairs]
    chain = ["qec_sample", "qec_train", "qec_compare"]
    if names not in (chain, chain + ["qec_read_report"]):
        raise ValueError("expected unique sample/train/compare chain")
    sample, train, compare = pairs[:3]
    dataset, checkpoint = sample["result"]["artifact_id"], train["result"]["artifact_id"]
    args, report = compare["args"], compare["result"]
    if (args["benchmark"] != {"warmup": 0, "repeats": 1, "batch_size": 32,
                              "device": "cpu", "threads": 1} or args["allow_cross_p"]):
        raise ValueError("comparison scientific defaults mismatch")
    if (train["args"]["dataset_id"] != dataset or args["dataset_id"] != dataset
            or args["checkpoint_ids"] != [checkpoint] or report["dataset_id"] != dataset):
        raise ValueError("dataset/checkpoint lineage mismatch")
    config = normalize_request("qec_sample", {"circuit": report["config"],
                                            "sampling": sample["args"]["sampling"]})
    if config != sample["args"]:
        raise ValueError("report circuit mismatch")
    if (report["benchmark"] != args["benchmark"]
            or report["allow_cross_p"] != args["allow_cross_p"]):
        raise ValueError("report comparison parameters mismatch")
    rows = report["results"]
    if (len(rows) != 3 or {r["decoder"] for r in rows} != {"mwpm", "lookup", "mlp"}
            or any(r.get("checkpoint_id") != (checkpoint if r["decoder"] == "mlp" else None)
                   or r["shots"] != sample["args"]["sampling"]["test_shots"] for r in rows)):
        raise ValueError("report checkpoint or sampling lineage mismatch")
    if len(pairs) == 4 and pairs[3]["result"] != report:
        raise ValueError("read report differs from comparison")
    return pairs


def assess_bound_qec(export):
    """New acceptance gate; does not rewrite legacy assessment outputs."""
    result = {"assessment_version": 2, "task_success": False, "failures": [], "bindings": []}
    try:
        pairs = bound_qec_execution(export["events"])
        result["bindings"] = [{"native_id": p["native_id"], "tool": p["tool"],
                               "endpoint": p["endpoint"], "args": p["args"],
                               "job_id": p["jobs"][-1]["id"] if p["jobs"] else None,
                               "artifact_id": p["result"]["artifact_id"]} for p in pairs]
        if not assess(export)["task_success"]:
            raise ValueError("historical scientific contract failed")
        result["task_success"] = True
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        result["failures"].append(type(exc).__name__ + ": " + str(exc))
    return result
