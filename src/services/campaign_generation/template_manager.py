"""
Template Manager Service - Handles campaign template storage and search.
"""
from typing import Dict, Any, List, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import logging
import uuid

from ...services.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class TemplateManager:
    """
    Manage campaign templates with semantic search using Qdrant.

    Responsibilities:
    - Store campaign templates in Qdrant
    - Search for similar templates using vector similarity
    - Track template usage and performance
    - Provide template recommendations
    """

    def __init__(
        self,
        qdrant_client: QdrantClient,
        embedding_service: Optional[EmbeddingService] = None,
        collection_name: str = "campaign_templates"
    ):
        """
        Initialize Template Manager.

        Args:
            qdrant_client: Qdrant client for vector storage
            embedding_service: Embedding service (uses Cohere embeddings by default)
            collection_name: Name of Qdrant collection
        """
        self.qdrant = qdrant_client
        self.embedding_service = embedding_service or EmbeddingService(provider="cohere")
        self.collection_name = collection_name
        self.embedding_dimensions = self.embedding_service.dimensions
        self.enabled = True  # Flag to indicate if template manager is working

        # Initialize collection if not exists
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Ensure Qdrant collection exists with proper configuration."""
        try:
            # Check if collection exists with timeout
            collections = self.qdrant.get_collections(timeout=5.0).collections
            exists = any(c.name == self.collection_name for c in collections)

            if not exists:
                logger.info(f"Creating Qdrant collection: {self.collection_name}")
                # Create collection with timeout
                self.qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dimensions,
                        distance=Distance.COSINE
                    ),
                    timeout=30.0  # 30 second timeout for collection creation
                )
                logger.info("Collection created successfully")
            else:
                logger.info(f"Collection {self.collection_name} already exists")

        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
            # Don't raise - allow the system to work without templates
            logger.warning("Template manager will work in limited mode without Qdrant")
            self.enabled = False

    async def add_template(
        self,
        template_id: str,
        name: str,
        description: str,
        category: str,
        template_json: Dict[str, Any],
        use_case: Optional[str] = None,
        avg_conversion_rate: Optional[float] = None,
        is_official: bool = False
    ) -> str:
        """
        Add a campaign template to the library.

        Args:
            template_id: Unique template identifier
            name: Template name
            description: Template description
            category: Template category (promotional, abandoned_cart, etc.)
            template_json: Campaign JSON structure
            use_case: Optional use case description
            avg_conversion_rate: Average conversion rate if known
            is_official: Whether this is an official template

        Returns:
            Vector ID in Qdrant

        Raises:
            Exception: If template storage fails
        """
        try:
            logger.info(f"Adding template: {name} ({template_id})")

            # Create searchable text from template
            search_text = self._create_search_text(
                name, description, category, use_case, template_json
            )

            # Generate embedding
            embedding = await self._embed_text(search_text)

            # Generate unique vector ID
            vector_id = str(uuid.uuid4())

            # Create point
            point = PointStruct(
                id=vector_id,
                vector=embedding,
                payload={
                    "template_id": template_id,
                    "name": name,
                    "description": description,
                    "category": category,
                    "use_case": use_case,
                    "template_json": template_json,
                    "avg_conversion_rate": avg_conversion_rate,
                    "is_official": is_official,
                    "times_used": 0
                }
            )

            # Upload to Qdrant
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=[point]
            )

            logger.info(f"Template added successfully with vector ID: {vector_id}")
            return vector_id

        except Exception as e:
            logger.error(f"Failed to add template: {e}")
            raise

    async def search_similar(
        self,
        query: str,
        campaign_type: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar campaign templates.

        Args:
            query: Search query (campaign description or intent)
            campaign_type: Optional filter by campaign type
            top_k: Number of results to return
            min_similarity: Minimum similarity score (0-1)

        Returns:
            List of similar templates with similarity scores

        Raises:
            Exception: If search fails
        """
        # Check if template manager is enabled
        if not self.enabled:
            logger.info("Template manager disabled - returning empty results")
            return []

        try:
            logger.info(f"Searching templates for: {query[:50]}...")

            # Generate query embedding
            query_embedding = await self._embed_text(query)

            # Build filter if campaign type specified
            query_filter = None
            if campaign_type:
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="category",
                            match=MatchValue(value=campaign_type)
                        )
                    ]
                )

            # Search in Qdrant
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=top_k,
                score_threshold=min_similarity
            )

            # Format results
            templates = []
            for result in results:
                template = {
                    "template_id": result.payload.get("template_id"),
                    "name": result.payload.get("name"),
                    "description": result.payload.get("description"),
                    "category": result.payload.get("category"),
                    "use_case": result.payload.get("use_case"),
                    "template_json": result.payload.get("template_json"),
                    "avg_conversion_rate": result.payload.get("avg_conversion_rate"),
                    "is_official": result.payload.get("is_official", False),
                    "times_used": result.payload.get("times_used", 0),
                    "similarity_score": result.score
                }
                templates.append(template)

            logger.info(f"Found {len(templates)} similar templates")
            return templates

        except Exception as e:
            logger.error(f"Template search failed: {e}")
            # Return empty list instead of failing
            return []

    async def increment_usage(self, template_id: str) -> None:
        """
        Increment the usage count for a template.

        Args:
            template_id: Template identifier
        """
        try:
            # Search for the template by ID
            results = self.qdrant.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="template_id",
                            match=MatchValue(value=template_id)
                        )
                    ]
                ),
                limit=1
            )

            if results[0]:
                point = results[0][0]
                # Update times_used
                current_count = point.payload.get("times_used", 0)
                point.payload["times_used"] = current_count + 1

                # Update in Qdrant
                self.qdrant.set_payload(
                    collection_name=self.collection_name,
                    payload={"times_used": current_count + 1},
                    points=[point.id]
                )

                logger.info(f"Incremented usage count for template {template_id}")

        except Exception as e:
            logger.warning(f"Failed to increment template usage: {e}")

    async def _embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for text using EmbeddingService.

        Args:
            text: Text to embed

        Returns:
            Embedding vector

        Raises:
            Exception: If embedding generation fails
        """
        try:
            embedding = await self.embedding_service.embed_text_async(text, use_cache=True)
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def _create_search_text(
        self,
        name: str,
        description: str,
        category: str,
        use_case: Optional[str],
        template_json: Dict[str, Any]
    ) -> str:
        """
        Create searchable text from template metadata.

        Args:
            name: Template name
            description: Template description
            category: Template category
            use_case: Use case description
            template_json: Campaign JSON

        Returns:
            Combined text for embedding
        """
        # Combine relevant text fields
        text_parts = [
            f"Name: {name}",
            f"Category: {category}",
            f"Description: {description}"
        ]

        if use_case:
            text_parts.append(f"Use case: {use_case}")

        # Add step count and types
        steps = template_json.get("steps", [])
        step_types = [s.get("type") for s in steps if s.get("type")]
        if step_types:
            text_parts.append(f"Flow: {' → '.join(step_types)}")

        return " | ".join(text_parts)

    def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific template by ID.

        Args:
            template_id: Template identifier

        Returns:
            Template dict or None if not found
        """
        try:
            results = self.qdrant.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="template_id",
                            match=MatchValue(value=template_id)
                        )
                    ]
                ),
                limit=1
            )

            if results[0]:
                point = results[0][0]
                return {
                    "template_id": point.payload.get("template_id"),
                    "name": point.payload.get("name"),
                    "description": point.payload.get("description"),
                    "category": point.payload.get("category"),
                    "template_json": point.payload.get("template_json"),
                    "avg_conversion_rate": point.payload.get("avg_conversion_rate"),
                    "times_used": point.payload.get("times_used", 0)
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get template {template_id}: {e}")
            return None

    async def seed_official_templates(self) -> None:
        """Seed the template library with official templates."""
        logger.info("Seeding official templates...")

        # Simple promotional template
        await self.add_template(
            template_id="official_promotional_simple",
            name="Simple Promotional Campaign",
            description="Basic promotional campaign with flash sale offer and reminder",
            category="promotional",
            use_case="Use for time-limited sales and promotions",
            template_json={
                "initialStepID": "step_001",
                "steps": [
                    {
                        "id": "step_001",
                        "type": "message",
                        "text": "{{merchant.name}}: Flash Sale! Get {{discount.amount}} off. Code: {{discount.code}}. Shop: {{merchant.url}}",
                        "events": [
                            {"id": "evt_001", "type": "click", "nextStepID": "step_end"},
                            {"id": "evt_002", "type": "noreply", "after": {"hours": 6}, "nextStepID": "step_002"}
                        ]
                    },
                    {
                        "id": "step_002",
                        "type": "message",
                        "text": "{{customer.first_name}}, don't miss out! {{discount.amount}} off ends soon. Code: {{discount.code}}",
                        "events": [
                            {"id": "evt_003", "type": "click", "nextStepID": "step_end"}
                        ]
                    },
                    {
                        "id": "step_end",
                        "type": "end",
                        "reason": "Campaign completed"
                    }
                ]
            },
            avg_conversion_rate=0.08,
            is_official=True
        )

        logger.info("Official templates seeded")


# Factory function
def create_template_manager(
    qdrant_url: str,
    qdrant_api_key: Optional[str] = None,
    provider: Optional[str] = None
) -> TemplateManager:
    """
    Factory function to create TemplateManager instance.

    Args:
        qdrant_url: Qdrant server URL
        qdrant_api_key: Optional Qdrant API key
        provider: Embedding provider ('openai' or 'cohere')

    Returns:
        Configured TemplateManager instance
    """
    qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    embedding_service = EmbeddingService(provider=provider)

    return TemplateManager(qdrant_client, embedding_service)