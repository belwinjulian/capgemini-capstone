"""Vertex AI Vector Search index + query client."""

from __future__ import annotations

from dataclasses import dataclass

from google.cloud import aiplatform


INDEX_DISPLAY_NAME = "patient-safety-index"
ENDPOINT_DISPLAY_NAME = "patient-safety-endpoint"
DEPLOYED_INDEX_ID = "patient_safety_v1"


@dataclass
class VectorSearchHandles:
    index_resource_name: str
    endpoint_resource_name: str
    deployed_index_id: str


def create_index(
    project: str,
    location: str,
    contents_delta_uri: str,
    dimensions: int = 768,
) -> aiplatform.MatchingEngineIndex:
    """Create a brute-force batch-update index from JSONL embeddings in GCS."""
    aiplatform.init(project=project, location=location)
    return aiplatform.MatchingEngineIndex.create_brute_force_index(
        display_name=INDEX_DISPLAY_NAME,
        contents_delta_uri=contents_delta_uri,
        dimensions=dimensions,
        distance_measure_type="DOT_PRODUCT_DISTANCE",
        index_update_method="BATCH_UPDATE",
        description="Patient safety corpus chunk embeddings (text-embedding-004, 768d)",
    )


def create_endpoint(project: str, location: str) -> aiplatform.MatchingEngineIndexEndpoint:
    aiplatform.init(project=project, location=location)
    return aiplatform.MatchingEngineIndexEndpoint.create(
        display_name=ENDPOINT_DISPLAY_NAME,
        public_endpoint_enabled=True,
    )


def deploy(
    endpoint: aiplatform.MatchingEngineIndexEndpoint,
    index: aiplatform.MatchingEngineIndex,
) -> aiplatform.MatchingEngineIndexEndpoint:
    return endpoint.deploy_index(
        index=index,
        deployed_index_id=DEPLOYED_INDEX_ID,
        display_name="Patient Safety Deployed Index v1",
        min_replica_count=1,
        max_replica_count=1,
    )


class VectorSearchClient:
    def __init__(self, project: str, location: str, endpoint_resource_name: str,
                 deployed_index_id: str = DEPLOYED_INDEX_ID):
        aiplatform.init(project=project, location=location)
        self.endpoint = aiplatform.MatchingEngineIndexEndpoint(endpoint_resource_name)
        self.deployed_index_id = deployed_index_id

    def query(self, embedding: list[float], k: int = 5) -> list[tuple[str, float]]:
        results = self.endpoint.find_neighbors(
            deployed_index_id=self.deployed_index_id,
            queries=[embedding],
            num_neighbors=k,
        )
        if not results:
            return []
        return [(m.id, float(m.distance)) for m in results[0]]


def teardown(project: str, location: str, endpoint_resource_name: str,
             index_resource_name: str) -> None:
    """Undeploy and delete the endpoint + index. Stops billing."""
    aiplatform.init(project=project, location=location)
    endpoint = aiplatform.MatchingEngineIndexEndpoint(endpoint_resource_name)
    endpoint.delete(force=True)
    index = aiplatform.MatchingEngineIndex(index_resource_name)
    index.delete()
