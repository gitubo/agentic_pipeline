import pytest
import json
from etcs_pipeline.core.runner import PipelineRunner

QUERY = (
    "Radio session establishment, train in SB mode at 0m from BG 2001, "
    "no active sections, request to establish communication with RBC"
)


@pytest.mark.integration
def test_session_establishment_pipeline_succeeds():
    runner = PipelineRunner("etcs")
    output = runner.run(QUERY)
    assert output.status == "SUCCESS", (
        f"Pipeline failed: {output.residual_errors}"
    )
    assert len(output.messages) >= 1
    assert output.validation_summary.formal_validation == "PASSED"


@pytest.mark.integration
def test_session_output_serializable():
    runner = PipelineRunner("etcs")
    output = runner.run(QUERY)
    json_str = output.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["status"] in ("SUCCESS", "PIPELINE_FAILURE")
