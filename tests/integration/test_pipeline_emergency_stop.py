import pytest
import json
from etcs_pipeline.core.runner import PipelineRunner

QUERY = "Emergency stop from RBC with train in FS mode at 150 km/h, train must halt immediately"


@pytest.mark.integration
def test_emergency_stop_pipeline_succeeds():
    runner = PipelineRunner("etcs")
    output = runner.run(QUERY)
    assert output.status == "SUCCESS", (
        f"Pipeline failed: {output.residual_errors}"
    )
    assert len(output.messages) >= 1
    assert output.validation_summary.formal_validation == "PASSED"


@pytest.mark.integration
def test_emergency_stop_output_serializable():
    runner = PipelineRunner("etcs")
    output = runner.run(QUERY)
    json_str = output.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["status"] in ("SUCCESS", "PIPELINE_FAILURE")
