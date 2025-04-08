import pytest
from unittest.mock import patch, MagicMock
from rag_pipelines import QA_pipeline
import rag_pipelines

@patch("rag_pipelines.ChatOpenAI")
@patch("rag_pipelines.ChatPromptTemplate")
@patch("rag_pipelines.BaseModel")
@patch("rag_pipelines.Field")
def test_QA_pipeline_with_mock(
    mock_Field,
    mock_BaseModel,
    mock_ChatPromptTemplate,
    mock_ChatOpenAI
):
    # Injecte pipeline_args directement
    rag_pipelines.pipeline_args = {
        "hybrid_pipeline_pp": "mock_pipeline_pp",
        "hybrid_pipeline_asso": "mock_pipeline_asso"
    }

    queries = [{
        "uid": "test-uid-123",
        "question": "Ville et pays ??",
        "size_answer": "",
        "enhanced_question": "",
        "question_is_open": "",
        "question_on_asso": "",
        "response": ""
    }]

    # Simulation du LLM
    mock_llm_instance = MagicMock()
    mock_llm_instance.with_structured_output.return_value = lambda x: {"type": "open"}
    mock_ChatOpenAI.return_value = mock_llm_instance
    mock_ChatPromptTemplate.from_messages.return_value = MagicMock()

    # Test du pipeline
    results = list(QA_pipeline(queries))

    assert isinstance(results, list)
    assert len(results) > 0
    for r in results:
        print("Résultat:", r)

