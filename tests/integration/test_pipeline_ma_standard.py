import pytest
import json
from etcs_pipeline.core.runner import PipelineRunner

QUERY = (
    "Train stopped in SR mode at 50m from BG 1001, "
    "two sections of 500m and 3000m, "
    "speed 80 km/h in station and 200 km/h on line, "
    "EOA at 3500m"
)


@pytest.mark.integration
def test_ma_standard_pipeline_succeeds():
    runner = PipelineRunner("etcs")
    output = runner.run(QUERY)
    assert output.status == "SUCCESS", (
        f"Pipeline failed: {output.residual_errors}"
    )
    assert len(output.messages) >= 3
    msg_types = [m.nid_message for m in output.messages]
    assert 0 in msg_types
    assert 3 in msg_types
    assert 8 in msg_types
    assert output.validation_summary.formal_validation == "PASSED"


@pytest.mark.integration
def test_ma_standard_output_serializable():
    runner = PipelineRunner("etcs")
    output = runner.run(QUERY)
    json_str = output.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["status"] in ("SUCCESS", "PIPELINE_FAILURE")
