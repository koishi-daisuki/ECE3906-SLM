import json
import time

from slm_adapter import Current, make_model_input
from slm_client import query_slm


current = Current(
    down=-5.0,
    battery=0.8,
    waypoint_index=1,
    waypoints=[
        ("origin", 0.0, 0.0, 0.0),
        ("A", 5.0, 5.0, -5.0),
        ("B", 10.0, 10.0, -5.0),
        ("C", 0.0, 10.0, -5.0),
        ("D", 10.0, 0.0, -5.0),
    ]
)

model_input = make_model_input(current)
print("Model input:")
print(json.dumps(model_input, indent=2))

TEST_COUNT = 5
expected = {
    "action": "continue_waypoint",
    "waypoint_id": "A",
}
records=[]
for i in range(TEST_COUNT):
    record = {
        "run": i + 1,
        "req_success": False,
        "correct": False,
        "client_request_ms": None,
        "decision": None,
        "error": None,
    }

    start_time = time.perf_counter()
    try:
        api_response = query_slm(model_input)
        latency = (time.perf_counter() - start_time) * 1000  # Convert to milliseconds
        record["req_success"] = True
        record["client_request_ms"] = latency
        record["raw_response"] = api_response
        decision = json.loads(api_response["message"]["content"])
        record["decision"] = decision
        record["correct"] = decision == expected        
    except Exception as e:
        if record["client_request_ms"] is None:
            record["client_request_ms"] = (time.perf_counter() - start_time) * 1000
        record["error"] = str(e)
    records.append(record)
    print(
        f"Run {record['run']}: "
        f"correct={record['correct']}, "
        f"latency={record['client_request_ms']:.2f} ms"
    )
    if record["error"]:
        print("Error:", record["error"])
    else:
        print(json.dumps(record["decision"]))

# calculate aggregate statistics
correct_count = sum(1 for r in records if r["correct"])
accuracy = correct_count / TEST_COUNT * 100
successful_count = sum(1 for r in records if r["req_success"])
average_latency = sum(r["client_request_ms"] for r in records if r["req_success"]) / successful_count if successful_count > 0 else None

summary = {
    "model_name": "qwen3.5:0.8b",
    "total_runs": TEST_COUNT,
    "successful_requests": successful_count,
    "failed_requests": TEST_COUNT - successful_count,
    "correct_decisions": correct_count,
    "accuracy": accuracy,
    "average_latency_ms": average_latency,
}

print("\nSummary:")
print(json.dumps(summary, indent=2))
# print(
#     "Matches expected:",
#     decision == {"action": "continue_waypoint", "waypoint_id": "A"}
# )
# print(f"client side total latency: {latency:.2f} ms")
# for field in (
#     "load_duration",
#     "prompt_eval_duration",
#     "eval_duration",
#     "total_duration",
# ):
#     duration = api_response.get(field)
#     if duration is not None:
#         print(f"{field}: {duration / 1_000_000:.2f} ms")
